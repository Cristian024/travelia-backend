from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import (
    CurrentUser,
    get_itinerary_service,
    get_packing_service,
)
from app.schemas.packing import PackingListResponse, SetPackingItemCheckedRequest
from app.schemas.itinerary import (
    AnswerReplacementRequest,
    DestinationQuestionsResponse,
    ItineraryResponse,
    ItinerarySummaryResponse,
    PublicFeedResponse,
    SetVisibilityRequest,
)
from app.services.itinerary_service import ItineraryService
from app.services.packing_service import PackingListService

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


@router.get("/public", response_model=PublicFeedResponse)
async def public_feed(
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
) -> PublicFeedResponse:
    """Feed público de inspiración: viajes marcados como públicos (paginado)."""
    items, total = await service.list_public(user_id=user_id, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return PublicFeedResponse(
        items=items, page=page, page_size=page_size, total=total, total_pages=total_pages
    )


@router.post("/{itinerary_id}/clone", response_model=ItineraryResponse, status_code=201)
async def clone_itinerary(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    """Copia un itinerario público (o propio) a la cuenta del usuario."""
    return await service.clone(user_id, itinerary_id)


@router.get("/{itinerary_id}/export/pdf")
async def export_itinerary_pdf(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> Response:
    """Convierte el itinerario (JSON) en un documento PDF."""
    pdf_bytes = await service.export_pdf(user_id, itinerary_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="itinerary-{itinerary_id}.pdf"'},
    )


@router.patch("/{itinerary_id}/visibility", response_model=ItineraryResponse)
async def set_visibility(
    itinerary_id: str,
    body: SetVisibilityRequest,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    """Marca/desmarca el itinerario como público para el feed de inspiración."""
    return await service.set_public(user_id, itinerary_id, body.is_public)


@router.get("/{itinerary_id}/packing-list", response_model=PackingListResponse)
async def get_packing_list(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[PackingListService, Depends(get_packing_service)],
) -> PackingListResponse:
    """Devuelve el checklist de equipaje guardado (404 si aún no se generó)."""
    packing = await service.get(user_id, itinerary_id)
    return PackingListResponse.from_domain(packing)


@router.post("/{itinerary_id}/packing-list", response_model=PackingListResponse)
async def generate_packing_list(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[PackingListService, Depends(get_packing_service)],
    regenerate: bool = Query(
        False, description="Fuerza una nueva generación aunque ya exista uno guardado."
    ),
) -> PackingListResponse:
    """Genera (y guarda) un checklist de equipaje. Si ya existe, lo devuelve
    guardado salvo que `regenerate=true`."""
    packing = await service.generate(user_id, itinerary_id, regenerate=regenerate)
    return PackingListResponse.from_domain(packing)


@router.patch(
    "/{itinerary_id}/packing-list/items/{position}",
    response_model=PackingListResponse,
)
async def set_packing_item_checked(
    itinerary_id: str,
    position: int,
    body: SetPackingItemCheckedRequest,
    user_id: CurrentUser,
    service: Annotated[PackingListService, Depends(get_packing_service)],
) -> PackingListResponse:
    """Marca/desmarca un item del checklist (checkbox) y persiste el cambio."""
    packing = await service.set_item_checked(user_id, itinerary_id, position, body.checked)
    return PackingListResponse.from_domain(packing)


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> ItineraryResponse:
    """Detalle del itinerario, incluyendo el pronóstico del clima."""
    return await service.get_itinerary(user_id, itinerary_id)


@router.delete("/{itinerary_id}", status_code=204)
async def delete_itinerary(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],
) -> None:
    """Deletes an itinerary along with all of its destinations."""
    await service.delete_itinerary(user_id, itinerary_id)


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
