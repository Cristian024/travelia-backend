import uuid
from datetime import datetime
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.llm.client import (
    LLMClient,
    build_destinations_from_llm,
    build_replacement_destination_from_llm,
)
from app.llm.decision_tree import DecisionTreeManager
from app.models.itinerary import DestinationReplacement, ItineraryDocument, ReplacementStatus
from app.models.planning import PlanningDocument, PlanningStatus, QuestionAnswer, QuestionTree
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.planning_repository import PlanningRepository
from app.schemas.itinerary import (
    AnswerReplacementRequest,
    DestinationQuestionsResponse,
    DestinationResponse,
    ItineraryResponse,
    ItinerarySummaryResponse,
)

MIN_REPLACEMENT_DEPTH = 1


class ItineraryService:
    def __init__(
        self,
        itinerary_repo: ItineraryRepository,
        planning_repo: PlanningRepository,
        llm: LLMClient,
    ) -> None:
        self._repo = itinerary_repo
        self._planning_repo = planning_repo
        self._llm = llm
        self._tree_mgr = DecisionTreeManager()

    async def generate_from_planning(self, user_id: str, planning_id: str) -> ItineraryResponse:
        planning = await self._get_owned_planning(user_id, planning_id)

        if planning.status == PlanningStatus.completed:
            raise BusinessRuleError("Planning already has a generated itinerary. Create a new planning session.")
        if planning.status == PlanningStatus.in_progress:
            raise BusinessRuleError("Planning is not marked as ready. Call /ready first.")

        current_node_id = planning.tree.current_node_id or planning.tree.root_id
        context = self._tree_mgr.build_context_summary(
            planning.general_answers, planning.tree, current_node_id
        )

        raw = self._llm.generate_itinerary_data(context, planning.general_answers)
        destinations = build_destinations_from_llm(raw.get("destinations", []))

        itinerary = ItineraryDocument(
            user_id=user_id,
            planning_id=planning_id,
            title=raw.get("title", "Mi itinerario de viaje"),
            summary=raw.get("summary", ""),
            arrival_date=planning.general_answers.arrival_date,
            departure_date=planning.general_answers.departure_date,
            total_days=planning.general_answers.total_days,
            destinations=destinations,
        )
        itinerary_id = await self._repo.insert(itinerary)
        itinerary.id = itinerary_id

        planning.status = PlanningStatus.completed
        planning.updated_at = datetime.utcnow()
        await self._planning_repo.save(planning)

        return _to_response(itinerary)

    async def list_itineraries(self, user_id: str) -> list[ItinerarySummaryResponse]:
        itineraries = await self._repo.find_by_user(user_id)
        return [_to_summary(it) for it in itineraries]

    async def get_itinerary(self, user_id: str, itinerary_id: str) -> ItineraryResponse:
        itinerary = await self._get_owned(user_id, itinerary_id)
        return _to_response(itinerary)

    # --- Destination replacement flow ---

    async def start_destination_replacement(
        self, user_id: str, itinerary_id: str, destination_id: str
    ) -> DestinationQuestionsResponse:
        itinerary = await self._get_owned(user_id, itinerary_id)
        dest = _find_dest(itinerary, destination_id)

        context = self._tree_mgr.build_context_summary(
            await self._get_planning_general(itinerary.planning_id),
            QuestionTree(),
            "",
        )
        replacement_context = self._llm.build_replacement_context(dest.replacement)
        questions = self._llm.generate_replacement_questions(dest, context, replacement_context, depth=0)

        tree, root = self._tree_mgr.create_root_node(questions)
        dest.replacement = DestinationReplacement(status=ReplacementStatus.in_progress, tree=tree)
        itinerary.updated_at = datetime.utcnow()
        await self._repo.save(itinerary)

        return DestinationQuestionsResponse(
            itinerary_id=itinerary_id,
            destination_id=destination_id,
            node_id=root.node_id,
            depth=0,
            questions=questions,
            can_replace=False,
        )

    async def answer_replacement_questions(
        self,
        user_id: str,
        itinerary_id: str,
        destination_id: str,
        request: AnswerReplacementRequest,
    ) -> DestinationQuestionsResponse:
        itinerary = await self._get_owned(user_id, itinerary_id)
        dest = _find_dest(itinerary, destination_id)

        if dest.replacement.status != ReplacementStatus.in_progress:
            raise BusinessRuleError("Replacement not in progress. Start replacement first.")

        tree = dest.replacement.tree
        self._tree_mgr.answer_node(tree, request.node_id, request.answers)

        general = await self._get_planning_general(itinerary.planning_id)
        context = self._tree_mgr.build_context_summary(general, QuestionTree(), "")
        replacement_context = self._llm.build_replacement_context(dest.replacement)

        answered_node = tree.nodes[request.node_id]
        next_depth = answered_node.depth + 1
        questions = self._llm.generate_replacement_questions(dest, context, replacement_context, depth=next_depth)
        child = self._tree_mgr.append_child_node(tree, request.node_id, questions)

        itinerary.updated_at = datetime.utcnow()
        await self._repo.save(itinerary)

        return DestinationQuestionsResponse(
            itinerary_id=itinerary_id,
            destination_id=destination_id,
            node_id=child.node_id,
            depth=child.depth,
            questions=questions,
            can_replace=child.depth >= MIN_REPLACEMENT_DEPTH,
        )

    async def replace_destination(
        self,
        user_id: str,
        itinerary_id: str,
        destination_id: str,
    ) -> ItineraryResponse:
        itinerary = await self._get_owned(user_id, itinerary_id)
        dest = _find_dest(itinerary, destination_id)

        if dest.replacement.status != ReplacementStatus.in_progress:
            raise BusinessRuleError("Replacement not started. Call start-replacement first.")

        tree = dest.replacement.tree
        if not tree.current_node_id or tree.nodes[tree.current_node_id].depth < MIN_REPLACEMENT_DEPTH:
            raise BusinessRuleError(
                f"Answer at least {MIN_REPLACEMENT_DEPTH} round(s) of replacement questions first."
            )

        general = await self._get_planning_general(itinerary.planning_id)
        context = self._tree_mgr.build_context_summary(general, QuestionTree(), "")
        replacement_answers = self._llm.build_replacement_context(dest.replacement)

        raw = self._llm.generate_replacement_destination(dest, context, replacement_answers)
        new_dest = build_replacement_destination_from_llm(raw, dest)

        idx = next(i for i, d in enumerate(itinerary.destinations) if d.destination_id == destination_id)
        itinerary.destinations[idx] = new_dest
        itinerary.updated_at = datetime.utcnow()
        await self._repo.save(itinerary)

        return _to_response(itinerary)

    async def _get_planning_general(self, planning_id: str):
        from app.models.planning import GeneralAnswers
        planning = await self._planning_repo.find_by_id(planning_id)
        if not planning:
            raise NotFoundError("Planning")
        return planning.general_answers

    async def _get_owned(self, user_id: str, itinerary_id: str) -> ItineraryDocument:
        it = await self._repo.find_by_id(itinerary_id)
        if not it:
            raise NotFoundError("Itinerary")
        if it.user_id != user_id:
            raise ForbiddenError()
        return it

    async def _get_owned_planning(self, user_id: str, planning_id: str) -> PlanningDocument:
        planning = await self._planning_repo.find_by_id(planning_id)
        if not planning:
            raise NotFoundError("Planning")
        if planning.user_id != user_id:
            raise ForbiddenError()
        return planning


def _find_dest(itinerary: ItineraryDocument, destination_id: str):
    for d in itinerary.destinations:
        if d.destination_id == destination_id:
            return d
    raise NotFoundError("Destination")


def _to_response(it: ItineraryDocument) -> ItineraryResponse:
    return ItineraryResponse(
        id=it.id,
        user_id=it.user_id,
        planning_id=it.planning_id,
        title=it.title,
        summary=it.summary,
        arrival_date=it.arrival_date,
        departure_date=it.departure_date,
        total_days=it.total_days,
        destinations=[DestinationResponse.from_domain(d) for d in it.destinations],
        status=it.status,
        created_at=it.created_at,
        updated_at=it.updated_at,
    )


def _to_summary(it: ItineraryDocument) -> ItinerarySummaryResponse:
    return ItinerarySummaryResponse(
        id=it.id,
        planning_id=it.planning_id,
        title=it.title,
        summary=it.summary,
        arrival_date=it.arrival_date,
        departure_date=it.departure_date,
        total_days=it.total_days,
        destination_count=len(it.destinations),
        status=it.status,
        created_at=it.created_at,
    )
