from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SubscriptionType(str, Enum):
    free = "FREE"
    premium = "PREMIUM"

class UserRole(str, Enum):
    user = "USER"
    admin = "ADMIN"

class LLMOperationType(str, Enum):
    questions = "questions"
    itinerary = "itinerary"


class UserDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    hashed_password: str
    full_name: str
    birth_date: str  # ISO date string YYYY-MM-DD
    country_of_residence: str
    phone: Optional[str] = None
    preferred_language: str = "es"
    subscription_type: SubscriptionType = SubscriptionType.free
    premium_since: Optional[datetime] = None
    role: UserRole = UserRole.user
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_premium(self) -> bool:
        return self.subscription_type == SubscriptionType.premium

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    class Config:
        populate_by_name = True
