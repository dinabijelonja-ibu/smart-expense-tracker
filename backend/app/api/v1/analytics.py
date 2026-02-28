from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import CategorySummaryResponse, ForecastResponse, MonthlySummaryResponse
from app.services.analytics_service import category_summary, forecast_end_of_month, monthly_summary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def monthly_summary_endpoint(
    month: date | None = Query(default=None, description="Optional date within target month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlySummaryResponse:
    result = monthly_summary(db, user_id=current_user.id, target=month)
    return MonthlySummaryResponse(**result)


@router.get("/category-summary", response_model=CategorySummaryResponse)
def category_summary_endpoint(
    month: date | None = Query(default=None, description="Optional date within target month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategorySummaryResponse:
    result = category_summary(db, user_id=current_user.id, target=month)
    return CategorySummaryResponse(**result)


@router.get("/forecast", response_model=ForecastResponse)
def forecast_endpoint(
    month: date | None = Query(default=None, description="Optional date within target month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ForecastResponse:
    result = forecast_end_of_month(db, user_id=current_user.id, target=month)
    return ForecastResponse(**result)
