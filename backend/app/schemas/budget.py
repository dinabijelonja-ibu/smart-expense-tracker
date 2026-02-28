from pydantic import BaseModel, Field


class BudgetCreateRequest(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    monthly_limit: float = Field(gt=0)


class BudgetResponse(BaseModel):
    id: int
    category: str
    monthly_limit: float
    spent_this_month: float
    usage_percent: float


class BudgetListResponse(BaseModel):
    items: list[BudgetResponse]
