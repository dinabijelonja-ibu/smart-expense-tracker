from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.expense import ExpenseCreateRequest, ExpenseListResponse, ExpenseResponse, ExpenseUpdateRequest
from app.services.expense_service import (
    create_expense,
    delete_expense,
    get_expense_category_map,
    list_expenses,
    serialize_expense,
    update_expense,
)

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense_endpoint(
    payload: ExpenseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    expense = create_expense(
        db,
        user_id=current_user.id,
        amount=payload.amount,
        category_name=payload.category,
        description=payload.description,
        expense_date=payload.date,
    )
    category_map = get_expense_category_map(db, [expense])
    return ExpenseResponse(**serialize_expense(expense, category_map.get(expense.category_id, "unknown")))


@router.get("", response_model=ExpenseListResponse)
def list_expenses_endpoint(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseListResponse:
    expenses = list_expenses(
        db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_name=category,
    )
    category_map = get_expense_category_map(db, expenses)
    return ExpenseListResponse(
        items=[ExpenseResponse(**serialize_expense(expense, category_map.get(expense.category_id, "unknown"))) for expense in expenses]
    )


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense_endpoint(
    expense_id: int,
    payload: ExpenseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpenseResponse:
    expense = update_expense(
        db,
        user_id=current_user.id,
        expense_id=expense_id,
        amount=payload.amount,
        category_name=payload.category,
        description=payload.description,
        expense_date=payload.date,
    )
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    category_map = get_expense_category_map(db, [expense])
    return ExpenseResponse(**serialize_expense(expense, category_map.get(expense.category_id, "unknown")))


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_endpoint(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = delete_expense(db, user_id=current_user.id, expense_id=expense_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
