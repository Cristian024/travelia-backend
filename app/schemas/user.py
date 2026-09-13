from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    birth_date: str  # YYYY-MM-DD
    country_of_residence: str
    phone: Optional[str] = None
    preferred_language: str = "es"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            from datetime import date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("birth_date must be in YYYY-MM-DD format")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    country_of_residence: Optional[str] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None

    @field_validator("birth_date")
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            from datetime import date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("birth_date must be in YYYY-MM-DD format")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    birth_date: str
    country_of_residence: str
    phone: Optional[str]
    preferred_language: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
