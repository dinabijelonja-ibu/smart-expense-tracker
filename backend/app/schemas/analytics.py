from pydantic import BaseModel


class MonthlySummaryResponse(BaseModel):
    month: str
    total_spent: float
    expense_count: int
    average_daily_spend: float


class CategorySummaryItem(BaseModel):
    category: str
    total_spent: float


class CategorySummaryResponse(BaseModel):
    month: str
    items: list[CategorySummaryItem]


class ForecastResponse(BaseModel):
    month: str
    current_total: float
    days_elapsed: int
    remaining_days: int
    average_daily_spend: float
    projected_end_of_month_total: float
