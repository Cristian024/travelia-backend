from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from app.models.planning import QuestionTree


class ItineraryStatus(str, Enum):
    active = "active"
    archived = "archived"


class ReplacementStatus(str, Enum):
    none = "none"
    in_progress = "in_progress"


class Activity(BaseModel):
    activity_id: str
    name: str
    description: str
    duration_hours: float
    category: str
    estimated_cost: Optional[str] = None


class DestinationReplacement(BaseModel):
    status: ReplacementStatus = ReplacementStatus.none
    tree: QuestionTree = Field(default_factory=QuestionTree)


class Destination(BaseModel):
    destination_id: str
    order: int
    name: str
    country: str
    city: str
    days_allocated: int
    description: str
    highlights: list[str] = Field(default_factory=list)
    accommodation_suggestions: list[str] = Field(default_factory=list)
    transportation: str = ""
    estimated_cost: Optional[str] = None
    activities: list[Activity] = Field(default_factory=list)
    replacement: DestinationReplacement = Field(default_factory=DestinationReplacement)


class ItineraryDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    planning_id: str
    title: str
    summary: str
    arrival_date: str
    departure_date: str
    total_days: int
    destinations: list[Destination] = Field(default_factory=list)
    status: ItineraryStatus = ItineraryStatus.active
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
