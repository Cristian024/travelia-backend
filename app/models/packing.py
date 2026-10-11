from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PackingItem(BaseModel):
    category: str
    item: str
    quantity: Optional[str] = None
    reason: Optional[str] = None
    checked: bool = False


class PackingList(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    itinerary_id: str
    destination_summary: str
    weather_summary: str = ""
    items: list[PackingItem] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
