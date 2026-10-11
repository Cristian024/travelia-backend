from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_expense_service
from app.schemas.expense import (
    CreateExpenseRequest,
    ExpenseResponse,
    ExpenseSummaryResponse,
    UpdateExpenseRequest,
)
from app.services.expense_service import ExpenseService

router = APIRouter(tags=["Expenses"])


@router.post(
    "/itineraries/{itinerary_id}/expenses",
    response_model=ExpenseResponse,
    status_code=201,
)
async def create_expense(
    itinerary_id: str,
    body: CreateExpenseRequest,
    user_id: CurrentUser,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseResponse:
    return await service.create(user_id, itinerary_id, body)


@router.get("/itineraries/{itinerary_id}/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> list[ExpenseResponse]:
    return await service.list(user_id, itinerary_id)


@router.get(
    "/itineraries/{itinerary_id}/expenses/summary",
    response_model=ExpenseSummaryResponse,
)
async def expenses_summary(
    itinerary_id: str,
    user_id: CurrentUser,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseSummaryResponse:
    """Resumen comparativo de gastos reales vs. estimated_cost del itinerario."""
    return await service.summary(user_id, itinerary_id)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    body: UpdateExpenseRequest,
    user_id: CurrentUser,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> ExpenseResponse:
    return await service.update(user_id, expense_id, body)


@router.delete("/expenses/{expense_id}", status_code=204)
async def delete_expense(
    expense_id: str,
    user_id: CurrentUser,
    service: Annotated[ExpenseService, Depends(get_expense_service)],
) -> None:
    await service.delete(user_id, expense_id)
