from typing import Annotated
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, get_planning_service
from app.schemas.planning import (
    AnswerQuestionsRequest,
    CreatePlanningRequest,
    CurrentQuestionsResponse,
    GENERAL_QUESTIONS,
    PlanningResponse,
    QuestionTreeResponse,
)
from app.services.planning_service import PlanningService

router = APIRouter(prefix="/planning", tags=["Planning"])


@router.get("/general-questions")
async def get_general_questions() -> list[dict]:
    """Returns the fixed list of general questions that start every planning session."""
    return GENERAL_QUESTIONS


@router.post("/", response_model=PlanningResponse, status_code=201)
async def create_planning(
    body: CreatePlanningRequest,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanningResponse:
    """Creates a new planning session with general answers and returns the first dynamic question group."""
    return await service.create_planning(user_id, body)


@router.get("/{planning_id}", response_model=PlanningResponse)
async def get_planning(
    planning_id: str,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanningResponse:
    return await service.get_planning(user_id, planning_id)


@router.get("/{planning_id}/current-questions", response_model=CurrentQuestionsResponse)
async def get_current_questions(
    planning_id: str,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> CurrentQuestionsResponse:
    """Returns the current pending question group for the user to answer."""
    return await service.get_current_questions(user_id, planning_id)


@router.post("/{planning_id}/answer", response_model=CurrentQuestionsResponse)
async def answer_questions(
    planning_id: str,
    body: AnswerQuestionsRequest,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> CurrentQuestionsResponse:
    """
    Submits answers to the current question group. The LLM generates the next
    group of dynamic questions and advances the decision tree one level deeper.
    """
    return await service.answer_questions(user_id, planning_id, body)


@router.post("/{planning_id}/ready", response_model=PlanningResponse)
async def mark_ready_to_generate(
    planning_id: str,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> PlanningResponse:
    """
    Signals that the user has enough information and wants to generate the itinerary.
    The planning must have at least one round of answered dynamic questions.
    """
    return await service.mark_ready(user_id, planning_id)


@router.get("/{planning_id}/tree", response_model=QuestionTreeResponse)
async def get_decision_tree(
    planning_id: str,
    user_id: CurrentUser,
    service: Annotated[PlanningService, Depends(get_planning_service)],
) -> QuestionTreeResponse:
    """Returns the full decision tree structure for a planning session."""
    return await service.get_tree(user_id, planning_id)
