from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.automation import (
    BudgetAlertsResponse,
    ReceiptIngestRequest,
    ReceiptIngestResponse,
    WeeklyReportResponse,
)
from app.services.automation_service import build_weekly_report_data, get_budget_alerts, ingest_receipt_expense

router = APIRouter(prefix="/automation", tags=["automation"])


def verify_automation_key(x_automation_key: str | None = Header(default=None)) -> None:
    if not settings.automation_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTOMATION_API_KEY is not configured",
        )
    if x_automation_key != settings.automation_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid automation key")


@router.get("/weekly-report", response_model=WeeklyReportResponse, dependencies=[Depends(verify_automation_key)])
def weekly_report_endpoint(
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
) -> WeeklyReportResponse:
    report = build_weekly_report_data(db, user_id=user_id)
    return WeeklyReportResponse(**report)


@router.get("/budget-alerts", response_model=BudgetAlertsResponse, dependencies=[Depends(verify_automation_key)])
def budget_alerts_endpoint(
    user_id: UUID = Query(...),
    threshold: float = Query(default=80.0, ge=1.0, le=100.0),
    db: Session = Depends(get_db),
) -> BudgetAlertsResponse:
    data = get_budget_alerts(db, user_id=user_id, threshold=threshold)
    return BudgetAlertsResponse(**data)


@router.post("/receipt-ingest", response_model=ReceiptIngestResponse, dependencies=[Depends(verify_automation_key)])
def receipt_ingest_endpoint(
    payload: ReceiptIngestRequest,
    db: Session = Depends(get_db),
) -> ReceiptIngestResponse:
    result = ingest_receipt_expense(
        db,
        user_id=payload.user_id,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
        expense_date=payload.date,
    )
    return ReceiptIngestResponse(**result)
