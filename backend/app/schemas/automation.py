from datetime import date

from pydantic import BaseModel, Field


class WeeklyReportResponse(BaseModel):
    user_id: str
    month: str
    total_spent: float
    expense_count: int
    average_daily_spend: float
    top_categories: list[dict]


class BudgetAlertItem(BaseModel):
    category: str
    monthly_limit: float
    spent_this_month: float
    usage_percent: float


class BudgetAlertsResponse(BaseModel):
    user_id: str
    threshold: float
    triggered: list[BudgetAlertItem]


class ReceiptIngestRequest(BaseModel):
    user_id: str
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    date: date


class ReceiptIngestResponse(BaseModel):
    expense_id: int
    status: str
