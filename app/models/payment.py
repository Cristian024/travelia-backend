from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    pending = "PENDING"
    approved = "APPROVED"
    declined = "DECLINED"
    voided = "VOIDED"
    error = "ERROR"


class Payment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    reference: str
    amount_in_cents: int
    currency: str = "COP"
    status: PaymentStatus = PaymentStatus.pending
    transaction_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
