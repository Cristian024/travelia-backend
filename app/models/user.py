from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.models.plan import PlanCode


class UserRole(str, Enum):
    """Rol derivado de la tabla/colección donde vive la cuenta."""
    user = "USER"
    admin = "ADMIN"


class LLMOperationType(str, Enum):
    questions = "questions"
    itinerary = "itinerary"


class UserDocument(BaseModel):
    """
    Modelo de dominio de una cuenta (cliente o administrador).

    Físicamente las cuentas viven separadas en `clients` y `admins`; el
    repositorio las unifica en este modelo para que los servicios no cambien.
    Los administradores solo rellenan los campos mínimos (los personales y de
    suscripción quedan con sus valores por defecto).
    """

    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    hashed_password: str
    full_name: str
    birth_date: str = ""  # YYYY-MM-DD (solo clientes)
    country_of_residence: str = ""  # solo clientes
    phone: Optional[str] = None
    preferred_language: str = "es"
    subscription_type: str = PlanCode.FREE
    premium_since: Optional[datetime] = None
    role: UserRole = UserRole.user
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_premium(self) -> bool:
        return self.subscription_type == PlanCode.PREMIUM

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    class Config:
        populate_by_name = True
