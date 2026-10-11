from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExpenseCategory(str, Enum):
    food = "food"
    transport = "transport"
    accommodation = "accommodation"
    activities = "activities"
    shopping = "shopping"
    other = "other"


class Expense(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    itinerary_id: str
    user_id: str
    category: ExpenseCategory
    description: str
    amount: float
    currency: str = "USD"
    expense_date: str  # ISO date string YYYY-MM-DD
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
