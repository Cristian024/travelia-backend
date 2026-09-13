from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    text = "text"
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    scale = "scale"
    date = "date"
    number = "number"


class PlanningStatus(str, Enum):
    in_progress = "in_progress"
    ready_to_generate = "ready_to_generate"
    completed = "completed"


class BudgetRange(str, Enum):
    economic = "economic"
    moderate = "moderate"
    luxury = "luxury"


class TravelPurpose(str, Enum):
    leisure = "leisure"
    adventure = "adventure"
    rest = "rest"
    business = "business"
    cultural = "cultural"
    gastronomic = "gastronomic"
    romantic = "romantic"
    family = "family"


class DynamicQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: QuestionType
    options: Optional[list[str]] = None
    required: bool = True


class QuestionAnswer(BaseModel):
    question_id: str
    answer: Any  # str | list[str] | int | float


class GeneralAnswers(BaseModel):
    destination_country: str
    destination_city: Optional[str] = None
    arrival_date: str
    departure_date: str
    total_days: int
    number_of_travelers: int
    budget_range: BudgetRange
    travel_purpose: TravelPurpose
    has_children: bool = False
    special_requirements: Optional[str] = None


# --- Decision Tree Node ---

class QuestionTreeNode(BaseModel):
    """
    Each node in the decision tree represents one round of LLM-generated
    questions. The tree grows downward as the user answers each group.
    """
    node_id: str
    parent_id: Optional[str] = None
    depth: int = 0
    questions: list[DynamicQuestion] = Field(default_factory=list)
    answers: Optional[list[QuestionAnswer]] = None
    children_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    answered_at: Optional[datetime] = None

    def is_answered(self) -> bool:
        return self.answers is not None and len(self.answers) > 0


class QuestionTree(BaseModel):
    nodes: dict[str, QuestionTreeNode] = Field(default_factory=dict)
    root_id: Optional[str] = None
    current_node_id: Optional[str] = None

    def get_node(self, node_id: str) -> Optional[QuestionTreeNode]:
        return self.nodes.get(node_id)

    def get_current_node(self) -> Optional[QuestionTreeNode]:
        if self.current_node_id:
            return self.nodes.get(self.current_node_id)
        return None

    def get_path_to_node(self, node_id: str) -> list[QuestionTreeNode]:
        """Returns all nodes from root down to the given node (inclusive)."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        path: list[QuestionTreeNode] = []
        current: Optional[QuestionTreeNode] = node
        while current:
            path.append(current)
            current = self.nodes.get(current.parent_id) if current.parent_id else None
        return list(reversed(path))

    def collect_all_answers(self) -> list[QuestionAnswer]:
        """Collects all answers along the current path from root."""
        if not self.current_node_id:
            return []
        path = self.get_path_to_node(self.current_node_id)
        answers: list[QuestionAnswer] = []
        for node in path:
            if node.answers:
                answers.extend(node.answers)
        return answers

    def add_node(self, node: QuestionTreeNode) -> None:
        self.nodes[node.node_id] = node
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.node_id not in parent.children_ids:
                parent.children_ids.append(node.node_id)


class PlanningDocument(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    status: PlanningStatus = PlanningStatus.in_progress
    general_answers: GeneralAnswers
    tree: QuestionTree = Field(default_factory=QuestionTree)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
