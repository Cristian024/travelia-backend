from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator, model_validator
from app.models.planning import (
    BudgetRange,
    DynamicQuestion,
    GeneralAnswers,
    PlanningStatus,
    QuestionAnswer,
    QuestionTree,
    QuestionTreeNode,
    TravelPurpose,
)


# --- Static general questions definition ---

GENERAL_QUESTIONS = [
    {
        "id": "destination_country",
        "label": "¿A qué país deseas viajar?",
        "type": "text",
        "required": True,
    },
    {
        "id": "destination_city",
        "label": "¿Tienes alguna ciudad o región específica en mente?",
        "type": "text",
        "required": False,
    },
    {
        "id": "arrival_date",
        "label": "¿Cuál es tu fecha de llegada?",
        "type": "date",
        "required": True,
    },
    {
        "id": "departure_date",
        "label": "¿Cuál es tu fecha de salida?",
        "type": "date",
        "required": True,
    },
    {
        "id": "number_of_travelers",
        "label": "¿Cuántas personas viajan?",
        "type": "number",
        "required": True,
    },
    {
        "id": "budget_range",
        "label": "¿Cuál es tu rango de presupuesto?",
        "type": "single_choice",
        "options": ["economic", "moderate", "luxury"],
        "required": True,
    },
    {
        "id": "travel_purpose",
        "label": "¿Cuál es el propósito principal de tu viaje?",
        "type": "single_choice",
        "options": ["leisure", "adventure", "rest", "business", "cultural", "gastronomic", "romantic", "family"],
        "required": True,
    },
    {
        "id": "has_children",
        "label": "¿Viajan niños?",
        "type": "single_choice",
        "options": ["true", "false"],
        "required": True,
    },
    {
        "id": "special_requirements",
        "label": "¿Tienes algún requerimiento especial (movilidad reducida, dietas, alergias, etc.)?",
        "type": "text",
        "required": False,
    },
]


# --- Request Schemas ---

class CreatePlanningRequest(BaseModel):
    destination_country: str
    destination_city: Optional[str] = None
    arrival_date: str
    departure_date: str
    number_of_travelers: int
    budget_range: BudgetRange
    travel_purpose: TravelPurpose
    has_children: bool = False
    special_requirements: Optional[str] = None

    @field_validator("arrival_date", "departure_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            from datetime import date
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_duration(self) -> "CreatePlanningRequest":
        from datetime import date

        arrival = date.fromisoformat(self.arrival_date)
        departure = date.fromisoformat(self.departure_date)
        if departure <= arrival:
            raise ValueError("departure_date must be after arrival_date")

        total_days = (departure - arrival).days
        # Tope absoluto (plan PREMIUM). El límite de 4 días para FREE se aplica
        # en PlanningService conociendo la suscripción del usuario.
        if total_days > 30:
            raise ValueError("total_days cannot exceed 30 days")
        return self


class AnswerQuestionsRequest(BaseModel):
    node_id: str
    answers: list[QuestionAnswer]


# --- Response Schemas ---

class QuestionTreeNodeResponse(BaseModel):
    node_id: str
    parent_id: Optional[str]
    depth: int
    questions: list[DynamicQuestion]
    answers: Optional[list[QuestionAnswer]]
    children_ids: list[str]
    is_answered: bool
    created_at: datetime
    answered_at: Optional[datetime]

    @classmethod
    def from_domain(cls, node: QuestionTreeNode) -> "QuestionTreeNodeResponse":
        return cls(
            node_id=node.node_id,
            parent_id=node.parent_id,
            depth=node.depth,
            questions=node.questions,
            answers=node.answers,
            children_ids=node.children_ids,
            is_answered=node.is_answered(),
            created_at=node.created_at,
            answered_at=node.answered_at,
        )


class QuestionTreeResponse(BaseModel):
    root_id: Optional[str]
    current_node_id: Optional[str]
    nodes: dict[str, QuestionTreeNodeResponse]

    @classmethod
    def from_domain(cls, tree: QuestionTree) -> "QuestionTreeResponse":
        return cls(
            root_id=tree.root_id,
            current_node_id=tree.current_node_id,
            nodes={nid: QuestionTreeNodeResponse.from_domain(n) for nid, n in tree.nodes.items()},
        )


class PlanningResponse(BaseModel):
    id: str
    user_id: str
    status: PlanningStatus
    general_answers: GeneralAnswers
    tree: QuestionTreeResponse
    created_at: datetime
    updated_at: datetime


class CurrentQuestionsResponse(BaseModel):
    planning_id: str
    node_id: str
    depth: int
    questions: list[DynamicQuestion]
    can_generate_itinerary: bool
