from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.plan import Plan


class PlanResponse(BaseModel):
    id: str
    code: str
    name: str
    amount_in_cents: int
    currency: str
    duration_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, plan: Plan) -> "PlanResponse":
        return cls(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            amount_in_cents=plan.amount_in_cents,
            currency=plan.currency,
            duration_days=plan.duration_days,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )


class CreatePlanRequest(BaseModel):
    code: str
    name: str
    amount_in_cents: int
    currency: str = "COP"
    duration_days: int = 30
    is_active: bool = True


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = None
    amount_in_cents: Optional[int] = None
    currency: Optional[str] = None
    duration_days: Optional[int] = None
    is_active: Optional[bool] = None
