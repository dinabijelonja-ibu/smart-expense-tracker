import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense
from app.services.common import get_or_create_category, normalize_category_name


def _to_float(value: Decimal | float) -> float:
    return float(value)


def create_expense(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount: float,
    category_name: str,
    description: str | None,
    expense_date: date,
) -> Expense:
    category = get_or_create_category(db, user_id=user_id, category_name=category_name)
    expense = Expense(
        user_id=user_id,
        category_id=category.id,
        amount=amount,
        description=description,
        date=expense_date,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def list_expenses(
    db: Session,
    *,
    user_id: uuid.UUID,
    start_date: date | None,
    end_date: date | None,
    category_name: str | None,
) -> list[Expense]:
    query: Select[tuple[Expense]] = select(Expense).where(Expense.user_id == user_id)

    if start_date:
        query = query.where(Expense.date >= start_date)
    if end_date:
        query = query.where(Expense.date <= end_date)
    if category_name:
        normalized = normalize_category_name(category_name)
        query = query.join(Category, Category.id == Expense.category_id).where(Category.name == normalized)

    query = query.order_by(Expense.date.desc(), Expense.id.desc())
    return list(db.scalars(query).all())


def update_expense(
    db: Session,
    *,
    user_id: uuid.UUID,
    expense_id: int,
    amount: float | None,
    category_name: str | None,
    description: str | None,
    expense_date: date | None,
) -> Expense | None:
    expense = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id))
    if not expense:
        return None

    if amount is not None:
        expense.amount = amount
    if description is not None:
        expense.description = description
    if expense_date is not None:
        expense.date = expense_date
    if category_name is not None:
        category = get_or_create_category(db, user_id=user_id, category_name=category_name)
        expense.category_id = category.id

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, *, user_id: uuid.UUID, expense_id: int) -> bool:
    expense = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id))
    if not expense:
        return False

    db.delete(expense)
    db.commit()
    return True


def get_expense_category_map(db: Session, expenses: list[Expense]) -> dict[int, str]:
    category_ids = {expense.category_id for expense in expenses}
    if not category_ids:
        return {}

    categories = db.scalars(select(Category).where(Category.id.in_(category_ids))).all()
    return {category.id: category.name for category in categories}


def serialize_expense(expense: Expense, category_name: str) -> dict:
    return {
        "id": expense.id,
        "amount": _to_float(expense.amount),
        "category": category_name,
        "description": expense.description,
        "date": expense.date,
        "created_at": expense.created_at,
    }
