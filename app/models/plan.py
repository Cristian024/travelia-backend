from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanCode:
    """Códigos de plan soportados (capa de dominio)."""

    FREE = "FREE"
    PREMIUM = "PREMIUM"


class Plan(BaseModel):
    """Plan comercial. El precio vive en base de datos, no en el código."""

    id: Optional[str] = Field(default=None, alias="_id")
    code: str
    name: str
    amount_in_cents: int
    currency: str = "COP"
    duration_days: int = 30
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
