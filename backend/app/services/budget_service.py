import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.category import Category
from app.models.expense import Expense
from app.services.common import get_or_create_category


def _to_float(value: Decimal | float) -> float:
    return float(value)


def create_or_update_budget(
    db: Session,
    *,
    user_id: uuid.UUID,
    category_name: str,
    monthly_limit: float,
) -> Budget:
    category = get_or_create_category(db, user_id=user_id, category_name=category_name)
    budget = db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.category_id == category.id))

    if budget:
        budget.monthly_limit = monthly_limit
    else:
        budget = Budget(user_id=user_id, category_id=category.id, monthly_limit=monthly_limit)
        db.add(budget)

    db.commit()
    db.refresh(budget)
    return budget


def list_budgets_with_usage(db: Session, *, user_id: uuid.UUID, target_date: date | None = None) -> list[dict]:
    reference = target_date or date.today()
    month = reference.month
    year = reference.year

    budgets = list(db.scalars(select(Budget).where(Budget.user_id == user_id).order_by(Budget.id.asc())).all())
    if not budgets:
        return []

    category_ids = [budget.category_id for budget in budgets]
    category_map = {
        category.id: category.name
        for category in db.scalars(select(Category).where(Category.id.in_(category_ids))).all()
    }

    spending_rows = db.execute(
        select(Expense.category_id, func.coalesce(func.sum(Expense.amount), 0).label("spent"))
        .where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
            Expense.category_id.in_(category_ids),
        )
        .group_by(Expense.category_id)
    ).all()
    spent_by_category = {row.category_id: float(row.spent) for row in spending_rows}

    items: list[dict] = []
    for budget in budgets:
        monthly_limit = _to_float(budget.monthly_limit)
        spent = spent_by_category.get(budget.category_id, 0.0)
        usage_percent = (spent / monthly_limit * 100.0) if monthly_limit > 0 else 0.0
        items.append(
            {
                "id": budget.id,
                "category": category_map.get(budget.category_id, "unknown"),
                "monthly_limit": monthly_limit,
                "spent_this_month": spent,
                "usage_percent": round(usage_percent, 2),
            }
        )

    return items
