from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.itinerary import (
    Activity,
    Destination,
    DestinationReplacement,
    ItineraryStatus,
    ReplacementStatus,
)
from app.models.planning import DynamicQuestion, QuestionAnswer
from app.schemas.planning import QuestionTreeResponse


class ActivityResponse(BaseModel):
    activity_id: str
    name: str
    description: str
    duration_hours: float
    category: str
    estimated_cost: Optional[str]

    @classmethod
    def from_domain(cls, a: Activity) -> "ActivityResponse":
        return cls(**a.model_dump())


class DestinationReplacementResponse(BaseModel):
    status: ReplacementStatus
    current_node_id: Optional[str]
    tree: Optional[QuestionTreeResponse]

    @classmethod
    def from_domain(cls, r: DestinationReplacement) -> "DestinationReplacementResponse":
        return cls(
            status=r.status,
            current_node_id=r.tree.current_node_id,
            tree=QuestionTreeResponse.from_domain(r.tree) if r.tree.nodes else None,
        )


class DestinationResponse(BaseModel):
    destination_id: str
    order: int
    name: str
    country: str
    city: str
    days_allocated: int
    description: str
    highlights: list[str]
    accommodation_suggestions: list[str]
    transportation: str
    estimated_cost: Optional[str]
    activities: list[ActivityResponse]
    replacement: DestinationReplacementResponse

    @classmethod
    def from_domain(cls, d: Destination) -> "DestinationResponse":
        return cls(
            destination_id=d.destination_id,
            order=d.order,
            name=d.name,
            country=d.country,
            city=d.city,
            days_allocated=d.days_allocated,
            description=d.description,
            highlights=d.highlights,
            accommodation_suggestions=d.accommodation_suggestions,
            transportation=d.transportation,
            estimated_cost=d.estimated_cost,
            activities=[ActivityResponse.from_domain(a) for a in d.activities],
            replacement=DestinationReplacementResponse.from_domain(d.replacement),
        )


class ItineraryResponse(BaseModel):
    id: str
    user_id: str
    planning_id: str
    title: str
    summary: str
    arrival_date: str
    departure_date: str
    total_days: int
    destinations: list[DestinationResponse]
    status: ItineraryStatus
    created_at: datetime
    updated_at: datetime


class ItinerarySummaryResponse(BaseModel):
    id: str
    planning_id: str
    title: str
    summary: str
    arrival_date: str
    departure_date: str
    total_days: int
    destination_count: int
    status: ItineraryStatus
    created_at: datetime


class DestinationQuestionsResponse(BaseModel):
    itinerary_id: str
    destination_id: str
    node_id: str
    depth: int
    questions: list[DynamicQuestion]
    can_replace: bool


class AnswerReplacementRequest(BaseModel):
    node_id: str
    answers: list[QuestionAnswer]
