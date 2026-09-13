from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    hashed_password: str
    full_name: str
    birth_date: str  # ISO date string YYYY-MM-DD
    country_of_residence: str
    phone: Optional[str] = None
    preferred_language: str = "es"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
