from typing import Annotated
from fastapi import APIRouter, Depends
from app.dependencies import CurrentUser, get_itinerary_service
from app.schemas.itinerary import (
    AnswerReplacementRequest,
    DestinationQuestionsResponse,
    ItineraryResponse,
    ItinerarySummaryResponse,
)
from app.services.itinerary_service import ItineraryService

router = APIRouter(prefix="/itineraries", tags=["Itineraries"])


@router.post("/generate/{planning_id}", response_model=ItineraryResponse, status_code=201)
async def generate_itinerary(
    planning_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    """
    Generates a full itinerary from a completed planning session.
    The planning must be in 'ready_to_generate' status (call /planning/{id}/ready first).
    """
    return await service.generate_from_planning(user_id, planning_id)


@router.get("/", response_model=list[ItinerarySummaryResponse])
async def list_itineraries(
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> list[ItinerarySummaryResponse]:
    """Returns the user's itinerary history (summaries)."""
    return await service.list_itineraries(user_id)


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    return await service.get_itinerary(user_id, itinerary_id)


@router.post(
    "/{itinerary_id}/destinations/{destination_id}/start-replacement",
    response_model=DestinationQuestionsResponse,
)
async def start_destination_replacement(
    itinerary_id: str,
    destination_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> DestinationQuestionsResponse:
    """
    Starts the destination replacement flow. The LLM generates an initial set of
    questions to understand what alternative destination the user prefers.
    """
    return await service.start_destination_replacement(user_id, itinerary_id, destination_id)


@router.post(
    "/{itinerary_id}/destinations/{destination_id}/answer-replacement",
    response_model=DestinationQuestionsResponse,
)
async def answer_replacement_questions(
    itinerary_id: str,
    destination_id: str,
    body: AnswerReplacementRequest,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> DestinationQuestionsResponse:
    """
    Submits answers to replacement questions. The LLM generates the next round
    of refinement questions. Once can_replace is true, call /replace.
    """
    return await service.answer_replacement_questions(user_id, itinerary_id, destination_id, body)


@router.post(
    "/{itinerary_id}/destinations/{destination_id}/replace",
    response_model=ItineraryResponse,
)
async def replace_destination(
    itinerary_id: str,
    destination_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    """
    Uses all collected replacement preferences to generate a new destination
    and replaces it in the itinerary. Returns the updated full itinerary.
    """
    return await service.replace_destination(user_id, itinerary_id, destination_id)
