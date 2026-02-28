from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreateRequest, BudgetListResponse, BudgetResponse
from app.services.budget_service import create_or_update_budget, list_budgets_with_usage

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget_endpoint(
    payload: BudgetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    budget = create_or_update_budget(
        db,
        user_id=current_user.id,
        category_name=payload.category,
        monthly_limit=payload.monthly_limit,
    )
    items = list_budgets_with_usage(db, user_id=current_user.id)
    match = next((item for item in items if item["id"] == budget.id), None)
    if match:
        return BudgetResponse(**match)
    return BudgetResponse(
        id=budget.id,
        category=payload.category.strip().lower(),
        monthly_limit=float(budget.monthly_limit),
        spent_this_month=0.0,
        usage_percent=0.0,
    )


@router.get("", response_model=BudgetListResponse)
def list_budgets_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetListResponse:
    items = list_budgets_with_usage(db, user_id=current_user.id)
    return BudgetListResponse(items=[BudgetResponse(**item) for item in items])
