import calendar
import uuid
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense


def _month_bounds(target: date | None = None) -> tuple[int, int, int]:
    reference = target or date.today()
    days_in_month = calendar.monthrange(reference.year, reference.month)[1]
    return reference.year, reference.month, days_in_month


def monthly_summary(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> dict:
    year, month, _ = _month_bounds(target)
    total, count = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id)).where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
    ).one()

    today = target or date.today()
    days_elapsed = max(today.day, 1)
    total_spent = float(total)
    average_daily = total_spent / days_elapsed

    return {
        "month": f"{year:04d}-{month:02d}",
        "total_spent": round(total_spent, 2),
        "expense_count": int(count),
        "average_daily_spend": round(average_daily, 2),
    }


def category_summary(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> dict:
    year, month, _ = _month_bounds(target)
    rows = db.execute(
        select(Category.name, func.coalesce(func.sum(Expense.amount), 0).label("total"))
        .join(Category, Category.id == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
        .group_by(Category.name)
        .order_by(func.sum(Expense.amount).desc())
    ).all()

    items = [{"category": row.name, "total_spent": round(float(row.total), 2)} for row in rows]

    return {
        "month": f"{year:04d}-{month:02d}",
        "items": items,
    }


def forecast_end_of_month(db: Session, *, user_id: uuid.UUID, target: date | None = None) -> dict:
    today = target or date.today()
    year, month, days_in_month = _month_bounds(today)

    current_total = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
    )
    current_total_value = float(current_total)

    days_elapsed = max(today.day, 1)
    remaining_days = max(days_in_month - today.day, 0)
    average_daily_spend = current_total_value / days_elapsed
    projected_end = current_total_value + average_daily_spend * remaining_days

    return {
        "month": f"{year:04d}-{month:02d}",
        "current_total": round(current_total_value, 2),
        "days_elapsed": days_elapsed,
        "remaining_days": remaining_days,
        "average_daily_spend": round(average_daily_spend, 2),
        "projected_end_of_month_total": round(projected_end, 2),
    }
