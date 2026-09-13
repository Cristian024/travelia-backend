from datetime import datetime, date
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.llm.client import LLMClient
from app.llm.decision_tree import DecisionTreeManager
from app.models.planning import (
    GeneralAnswers,
    PlanningDocument,
    PlanningStatus,
    QuestionAnswer,
    QuestionTree,
)
from app.repositories.planning_repository import PlanningRepository
from app.schemas.planning import (
    AnswerQuestionsRequest,
    CreatePlanningRequest,
    CurrentQuestionsResponse,
    PlanningResponse,
    QuestionTreeResponse,
)

MIN_DEPTH_TO_GENERATE = 1  # user must answer at least one round of dynamic questions


class PlanningService:
    def __init__(self, planning_repo: PlanningRepository, llm: LLMClient) -> None:
        self._repo = planning_repo
        self._llm = llm
        self._tree_mgr = DecisionTreeManager()

    async def create_planning(self, user_id: str, request: CreatePlanningRequest) -> PlanningResponse:
        arrival = date.fromisoformat(request.arrival_date)
        departure = date.fromisoformat(request.departure_date)
        if departure <= arrival:
            raise BusinessRuleError("departure_date must be after arrival_date")

        total_days = (departure - arrival).days

        general = GeneralAnswers(
            destination_country=request.destination_country,
            destination_city=request.destination_city,
            arrival_date=request.arrival_date,
            departure_date=request.departure_date,
            total_days=total_days,
            number_of_travelers=request.number_of_travelers,
            budget_range=request.budget_range,
            travel_purpose=request.travel_purpose,
            has_children=request.has_children,
            special_requirements=request.special_requirements,
        )

        context = self._tree_mgr.build_context_summary(general, QuestionTree(), "")
        questions = self._llm.generate_dynamic_questions(context, depth=0)
        tree, root_node = self._tree_mgr.create_root_node(questions)

        planning = PlanningDocument(
            user_id=user_id,
            general_answers=general,
            tree=tree,
        )
        planning_id = await self._repo.insert(planning)
        planning.id = planning_id

        return _to_response(planning)

    async def get_planning(self, user_id: str, planning_id: str) -> PlanningResponse:
        planning = await self._get_owned(user_id, planning_id)
        return _to_response(planning)

    async def get_current_questions(self, user_id: str, planning_id: str) -> CurrentQuestionsResponse:
        planning = await self._get_owned(user_id, planning_id)
        _assert_in_progress(planning)

        current = planning.tree.get_current_node()
        if not current:
            raise BusinessRuleError("No active question node found")
        if current.is_answered():
            raise BusinessRuleError("Current node already answered. Retrieve next questions first.")

        can_generate = current.depth >= MIN_DEPTH_TO_GENERATE

        return CurrentQuestionsResponse(
            planning_id=planning_id,
            node_id=current.node_id,
            depth=current.depth,
            questions=current.questions,
            can_generate_itinerary=can_generate,
        )

    async def answer_questions(
        self,
        user_id: str,
        planning_id: str,
        request: AnswerQuestionsRequest,
    ) -> CurrentQuestionsResponse:
        planning = await self._get_owned(user_id, planning_id)
        _assert_in_progress(planning)

        self._tree_mgr.answer_node(planning.tree, request.node_id, request.answers)

        context = self._tree_mgr.build_context_summary(
            planning.general_answers, planning.tree, request.node_id
        )
        questions = self._llm.generate_dynamic_questions(context, depth=planning.tree.nodes[request.node_id].depth + 1)

        child = self._tree_mgr.append_child_node(planning.tree, request.node_id, questions)
        planning.updated_at = datetime.utcnow()
        await self._repo.save(planning)

        return CurrentQuestionsResponse(
            planning_id=planning_id,
            node_id=child.node_id,
            depth=child.depth,
            questions=child.questions,
            can_generate_itinerary=child.depth >= MIN_DEPTH_TO_GENERATE,
        )

    async def mark_ready(self, user_id: str, planning_id: str) -> PlanningResponse:
        planning = await self._get_owned(user_id, planning_id)
        _assert_in_progress(planning)

        current = planning.tree.get_current_node()
        if not current or current.depth < MIN_DEPTH_TO_GENERATE:
            raise BusinessRuleError(
                f"You must answer at least {MIN_DEPTH_TO_GENERATE} round(s) of dynamic questions before generating an itinerary."
            )

        planning.status = PlanningStatus.ready_to_generate
        planning.updated_at = datetime.utcnow()
        await self._repo.save(planning)
        return _to_response(planning)

    async def get_tree(self, user_id: str, planning_id: str) -> QuestionTreeResponse:
        planning = await self._get_owned(user_id, planning_id)
        return QuestionTreeResponse.from_domain(planning.tree)

    async def _get_owned(self, user_id: str, planning_id: str) -> PlanningDocument:
        planning = await self._repo.find_by_id(planning_id)
        if not planning:
            raise NotFoundError("Planning")
        if planning.user_id != user_id:
            raise ForbiddenError()
        return planning


def _assert_in_progress(planning: PlanningDocument) -> None:
    if planning.status != PlanningStatus.in_progress:
        raise BusinessRuleError(f"Planning is not in progress (status: {planning.status.value})")


def _to_response(planning: PlanningDocument) -> PlanningResponse:
    return PlanningResponse(
        id=planning.id,
        user_id=planning.user_id,
        status=planning.status,
        general_answers=planning.general_answers,
        tree=QuestionTreeResponse.from_domain(planning.tree),
        created_at=planning.created_at,
        updated_at=planning.updated_at,
    )
