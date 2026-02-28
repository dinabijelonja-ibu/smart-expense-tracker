import json
import uuid
from datetime import date
from urllib import error, request

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

    req = request.Request(
        f"{settings.llm_base_url.rstrip('/')}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RAGError(f"Embedding HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RAGError(f"Embedding request failed: {exc.reason}") from exc

    data = body.get("data", [])
    if not data:
        raise RAGError("Embedding API returned no data")

    vector = data[0].get("embedding")
    if not isinstance(vector, list):
        raise RAGError("Embedding API returned invalid vector")
    return vector


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
    vector = _request_embedding(content)

    key = f"monthly-summary:{reference.year:04d}-{reference.month:02d}"
    existing = db.scalar(
        select(Embedding).where(
            Embedding.user_id == user_id,
            Embedding.metadata_json["key"].astext == key,
        )
    )

    metadata = {
        "key": key,
        "year": reference.year,
        "month": reference.month,
        "type": "monthly_summary",
    }

    if existing:
        existing.content = content
        existing.embedding = vector
        existing.metadata_json = metadata
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": "updated", "content": content}

    row = Embedding(
        user_id=user_id,
        content=content,
        embedding=vector,
        metadata_json=metadata,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": "created", "content": content}


def retrieve_context(db: Session, *, user_id: uuid.UUID, question: str, top_k: int | None = None) -> list[str]:
    existing_count = db.scalar(select(func.count(Embedding.id)).where(Embedding.user_id == user_id))
    if not existing_count:
        rebuild_monthly_embedding(db, user_id=user_id)

    vector = _request_embedding(question)
    limit = top_k or settings.rag_top_k

    rows = db.scalars(
        select(Embedding)
        .where(Embedding.user_id == user_id)
        .order_by(Embedding.embedding.cosine_distance(vector))
        .limit(limit)
    ).all()

    return [row.content for row in rows]
