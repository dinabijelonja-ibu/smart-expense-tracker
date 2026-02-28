import uuid

from sqlalchemy.orm import Session

from app.services.analytics_service import category_summary, monthly_summary
from app.services.budget_service import list_budgets_with_usage
from app.services.expense_service import create_expense


def build_weekly_report_data(db: Session, *, user_id: uuid.UUID) -> dict:
    summary = monthly_summary(db, user_id=user_id)
    categories = category_summary(db, user_id=user_id)
    top_categories = categories["items"][:5]

    return {
        "user_id": str(user_id),
        "month": summary["month"],
        "total_spent": summary["total_spent"],
        "expense_count": summary["expense_count"],
        "average_daily_spend": summary["average_daily_spend"],
        "top_categories": top_categories,
    }


def get_budget_alerts(db: Session, *, user_id: uuid.UUID, threshold: float = 80.0) -> dict:
    usage_items = list_budgets_with_usage(db, user_id=user_id)
    triggered = [item for item in usage_items if item["usage_percent"] >= threshold]

    return {
        "user_id": str(user_id),
        "threshold": threshold,
        "triggered": triggered,
    }


def ingest_receipt_expense(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount: float,
    category: str,
    description: str | None,
    expense_date,
) -> dict:
    expense = create_expense(
        db,
        user_id=user_id,
        amount=amount,
        category_name=category,
        description=description,
        expense_date=expense_date,
    )

    return {
        "expense_id": expense.id,
        "status": "created",
    }
