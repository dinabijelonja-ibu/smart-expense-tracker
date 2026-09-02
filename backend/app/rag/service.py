import uuid
from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category
from app.models.embedding import Embedding
from app.models.expense import Expense


class RAGError(Exception):
    pass


def _request_embedding(text: str) -> list[float]:
    if not settings.llm_api_key:
        raise RAGError("LLM_API_KEY is not configured")

    payload = {
        "model": settings.embedding_model,
        "input": text,
    }

    try:
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/embeddings",
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=60,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RAGError(f"Embedding HTTP {exc.response.status_code}: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise RAGError(f"Embedding request failed: {exc}") from exc

    body = response.json()
    data = body.get("data", [])
    if not data:
        raise RAGError("Embedding API returned no data")

    vector = data[0].get("embedding")
    if not isinstance(vector, list):
        raise RAGError("Embedding API returned invalid vector")
    return vector


def _upsert_embedding(db: Session, *, user_id: uuid.UUID, key: str, content: str, metadata: dict) -> dict:
    """Create or refresh the single embedding row identified by `key` for this user.

    `key` (stored in `metadata_json["key"]`) is our own dedup identifier -- e.g.
    `expense:123`, `daily-summary:2026-09-02`, `monthly-summary:2026-09` -- so
    re-syncing the same document updates it in place instead of accumulating
    stale duplicates.
    """
    vector = _request_embedding(content)

    existing = db.scalar(
        select(Embedding).where(
            Embedding.user_id == user_id,
            Embedding.metadata_json["key"].astext == key,
        )
    )

    if existing:
        existing.content = content
        existing.embedding = vector
        existing.metadata_json = metadata
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": "updated", "content": content}

    row = Embedding(user_id=user_id, content=content, embedding=vector, metadata_json=metadata)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": "created", "content": content}


def _delete_embedding_by_key(db: Session, *, user_id: uuid.UUID, key: str) -> bool:
    existing = db.scalar(
        select(Embedding).where(
            Embedding.user_id == user_id,
            Embedding.metadata_json["key"].astext == key,
        )
    )
    if not existing:
        return False
    db.delete(existing)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Monthly summary embeddings (aggregate granularity -- "how did this month go")
# ---------------------------------------------------------------------------


def build_monthly_summary_text(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> str:
    reference = target or date.today()

    rows = db.execute(
        select(Category.name, func.coalesce(func.sum(Expense.amount), 0).label("total"))
        .join(Category, Category.id == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == reference.month,
            extract("year", Expense.date) == reference.year,
        )
        .group_by(Category.name)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    if not rows:
        return f"In {reference.strftime('%B %Y')} you have no recorded expenses yet."

    total = sum(float(row.total) for row in rows)
    formatted = ", ".join([f"{float(row.total):.2f} on {row.name}" for row in rows])
    return f"In {reference.strftime('%B %Y')} you spent {total:.2f} in total across categories: {formatted}."


def rebuild_monthly_embedding(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> dict:
    reference = target or date.today()
    content = build_monthly_summary_text(db, user_id=user_id, target=reference)
    key = f"monthly-summary:{reference.year:04d}-{reference.month:02d}"
    metadata = {
        "key": key,
        "year": reference.year,
        "month": reference.month,
        "type": "monthly_summary",
    }
    return _upsert_embedding(db, user_id=user_id, key=key, content=content, metadata=metadata)


# ---------------------------------------------------------------------------
# Daily summary embeddings (mid granularity -- "what happened on this day")
# ---------------------------------------------------------------------------


def build_daily_summary_text(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> str:
    reference = target or date.today()

    rows = db.execute(
        select(Category.name, func.coalesce(func.sum(Expense.amount), 0).label("total"))
        .join(Category, Category.id == Expense.category_id)
        .where(Expense.user_id == user_id, Expense.date == reference)
        .group_by(Category.name)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    if not rows:
        return f"On {reference.strftime('%B %d, %Y')} you have no recorded expenses."

    total = sum(float(row.total) for row in rows)
    formatted = ", ".join([f"{float(row.total):.2f} on {row.name}" for row in rows])
    return f"On {reference.strftime('%B %d, %Y')} you spent {total:.2f} in total across categories: {formatted}."


def rebuild_daily_embedding(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> dict:
    reference = target or date.today()
    content = build_daily_summary_text(db, user_id=user_id, target=reference)
    key = f"daily-summary:{reference.isoformat()}"
    metadata = {
        "key": key,
        "date": reference.isoformat(),
        "type": "daily_summary",
    }
    return _upsert_embedding(db, user_id=user_id, key=key, content=content, metadata=metadata)


# ---------------------------------------------------------------------------
# Per-expense embeddings (finest granularity -- "that coffee last Tuesday")
# ---------------------------------------------------------------------------


def build_expense_text(expense: Expense, category_name: str) -> str:
    amount = expense.amount if isinstance(expense.amount, Decimal) else Decimal(str(expense.amount))
    detail = f": {expense.description}" if expense.description else ""
    return f"On {expense.date.isoformat()} you spent {float(amount):.2f} on {category_name}{detail} (expense #{expense.id})."


def sync_expense_embedding(db: Session, *, expense: Expense, category_name: str) -> dict:
    content = build_expense_text(expense, category_name)
    key = f"expense:{expense.id}"
    metadata = {
        "key": key,
        "type": "expense",
        "expense_id": expense.id,
        "category": category_name,
        "date": expense.date.isoformat(),
    }
    return _upsert_embedding(db, user_id=expense.user_id, key=key, content=content, metadata=metadata)


def delete_expense_embedding(db: Session, *, user_id: uuid.UUID, expense_id: int) -> bool:
    return _delete_embedding_by_key(db, user_id=user_id, key=f"expense:{expense_id}")


# ---------------------------------------------------------------------------
# Write-time sync -- called from expense_service so every embedding
# granularity touched by a write stays fresh automatically, with no
# separate scheduler required. Both helpers are best-effort: RAG is a
# convenience layer for the AI chat, not part of the expense CRUD contract,
# so an unavailable/slow embeddings API must never block adding, editing,
# or deleting an expense.
# ---------------------------------------------------------------------------


def sync_expense_related_embeddings(db: Session, *, expense: Expense, category_name: str) -> None:
    try:
        sync_expense_embedding(db, expense=expense, category_name=category_name)
        rebuild_daily_embedding(db, user_id=expense.user_id, target=expense.date)
        rebuild_monthly_embedding(db, user_id=expense.user_id, target=expense.date)
    except RAGError:
        pass


def sync_expense_deletion(db: Session, *, user_id: uuid.UUID, expense_id: int, expense_date: date) -> None:
    try:
        delete_expense_embedding(db, user_id=user_id, expense_id=expense_id)
        rebuild_daily_embedding(db, user_id=user_id, target=expense_date)
        rebuild_monthly_embedding(db, user_id=user_id, target=expense_date)
    except RAGError:
        pass


def backfill_user_embeddings(db: Session, *, user_id: uuid.UUID) -> dict:
    """Rebuild every embedding granularity from a user's existing expense history.

    For onboarding this feature onto data that predates it, or recovering
    after the embeddings API was down for a while. Best-effort per document:
    one failed embedding call doesn't abort the rest of the backfill.
    """
    rows = db.execute(
        select(Expense, Category.name)
        .join(Category, Category.id == Expense.category_id)
        .where(Expense.user_id == user_id)
    ).all()

    days: set[date] = set()
    months: set[tuple[int, int]] = set()
    expenses_synced = 0

    for expense, category_name in rows:
        try:
            sync_expense_embedding(db, expense=expense, category_name=category_name)
            expenses_synced += 1
        except RAGError:
            pass
        days.add(expense.date)
        months.add((expense.date.year, expense.date.month))

    days_synced = 0
    for day in days:
        try:
            rebuild_daily_embedding(db, user_id=user_id, target=day)
            days_synced += 1
        except RAGError:
            pass

    months_synced = 0
    for year, month in months:
        try:
            rebuild_monthly_embedding(db, user_id=user_id, target=date(year, month, 1))
            months_synced += 1
        except RAGError:
            pass

    return {
        "expenses_total": len(rows),
        "expenses_synced": expenses_synced,
        "days_synced": days_synced,
        "months_synced": months_synced,
    }


def retrieve_context(db: Session, *, user_id: uuid.UUID, question: str, top_k: int | None = None) -> list[str]:
    existing_count = db.scalar(select(func.count(Embedding.id)).where(Embedding.user_id == user_id))
    if not existing_count:
        # Safety net for users whose history predates write-time sync, or
        # whose embedding calls have all failed so far.
        try:
            backfill_user_embeddings(db, user_id=user_id)
        except RAGError:
            pass

    vector = _request_embedding(question)
    limit = top_k or settings.rag_top_k

    rows = db.scalars(
        select(Embedding)
        .where(Embedding.user_id == user_id)
        .order_by(Embedding.embedding.cosine_distance(vector))
        .limit(limit)
    ).all()

    return [row.content for row in rows]
