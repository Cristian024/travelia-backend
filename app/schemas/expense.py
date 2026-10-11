from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.expense import Expense, ExpenseCategory


class CreateExpenseRequest(BaseModel):
    category: ExpenseCategory
    description: str
    amount: float
    currency: str = "USD"
    expense_date: str  # YYYY-MM-DD


class UpdateExpenseRequest(BaseModel):
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    expense_date: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    itinerary_id: str
    user_id: str
    category: ExpenseCategory
    description: str
    amount: float
    currency: str
    expense_date: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, e: Expense) -> "ExpenseResponse":
        return cls(
            id=e.id,
            itinerary_id=e.itinerary_id,
            user_id=e.user_id,
            category=e.category,
            description=e.description,
            amount=e.amount,
            currency=e.currency,
            expense_date=e.expense_date,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )


class CategoryBreakdown(BaseModel):
    category: str
    total: float


class ExpenseSummaryResponse(BaseModel):
    itinerary_id: str
    currency: str
    total_estimated: float
    total_real: float
    difference: float  # total_real - total_estimated
    status: str  # "under_budget" | "over_budget" | "on_budget"
    expenses_count: int
    by_category: list[CategoryBreakdown]
