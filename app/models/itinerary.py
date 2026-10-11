from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.planning import QuestionTree

# Solo se escapan los caracteres que rompen la query; el resto (incluidas
# tildes/unicode) se conserva tal cual.
_QUERY_ESCAPE_TABLE = str.maketrans(
    {
        " ": "%20",
        "&": "%26",
        "=": "%3D",
        "#": "%23",
        "+": "%2B",
        "%": "%25",
        "?": "%3F",
    }
)


def _encode_query_value(value: str) -> str:
    return value.translate(_QUERY_ESCAPE_TABLE)


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
    google_maps_url: Optional[str] = None
    replacement: DestinationReplacement = Field(default_factory=DestinationReplacement)

    @model_validator(mode="after")
    def _ensure_google_maps_url(self) -> "Destination":
        if not self.google_maps_url:
            self.google_maps_url = self._build_google_maps_url()
            
        return self

    def _build_google_maps_url(self) -> str:
        destination = ", ".join(p for p in (self.name, self.city, self.country) if p)
        params: list[tuple[str, str]] = [
            ("api", "1"),
            ("destination", destination),
            ("travelmode", "driving"),
        ]
        waypoints = [h for h in self.highlights[:8] if h]
        if waypoints:
            params.append(("waypoints", "|".join(waypoints)))
        query = "&".join(f"{key}={_encode_query_value(value)}" for key, value in params)
        return "https://www.google.com/maps/dir/?" + query


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
    is_public: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
