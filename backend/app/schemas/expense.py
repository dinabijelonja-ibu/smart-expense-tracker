from datetime import date as date_type, datetime

from pydantic import BaseModel, Field


class ExpenseCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    date: date_type


class ExpenseUpdateRequest(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    date: date_type | None = None


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: str | None
    date: date_type
    created_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseResponse]
