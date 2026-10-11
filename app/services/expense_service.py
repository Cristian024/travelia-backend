import re
from datetime import datetime
from typing import Optional

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.expense import Expense
from app.ports.repositories import ExpenseRepositoryPort, ItineraryRepositoryPort
from app.schemas.expense import (
    CategoryBreakdown,
    CreateExpenseRequest,
    ExpenseResponse,
    ExpenseSummaryResponse,
    UpdateExpenseRequest,
)


class ExpenseService:
    def __init__(
        self,
        expense_repo: ExpenseRepositoryPort,
        itinerary_repo: ItineraryRepositoryPort,
    ) -> None:
        self._repo = expense_repo
        self._itinerary_repo = itinerary_repo

    async def create(
        self, user_id: str, itinerary_id: str, request: CreateExpenseRequest
    ) -> ExpenseResponse:
        await self._assert_itinerary_owned(user_id, itinerary_id)
        expense = Expense(
            itinerary_id=itinerary_id,
            user_id=user_id,
            category=request.category,
            description=request.description,
            amount=request.amount,
            currency=request.currency,
            expense_date=request.expense_date,
        )
        expense_id = await self._repo.insert(expense)
        expense.id = expense_id
        return ExpenseResponse.from_domain(expense)

    async def list(self, user_id: str, itinerary_id: str) -> list[ExpenseResponse]:
        await self._assert_itinerary_owned(user_id, itinerary_id)
        expenses = await self._repo.find_by_itinerary(itinerary_id)
        return [ExpenseResponse.from_domain(e) for e in expenses]

    async def update(
        self, user_id: str, expense_id: str, request: UpdateExpenseRequest
    ) -> ExpenseResponse:
        expense = await self._get_owned(user_id, expense_id)
        updates = request.model_dump(exclude_none=True)
        if not updates:
            return ExpenseResponse.from_domain(expense)

        for field, value in updates.items():
            setattr(expense, field, value)
        expense.updated_at = datetime.utcnow()
        await self._repo.update(expense)
        return ExpenseResponse.from_domain(expense)

    async def delete(self, user_id: str, expense_id: str) -> None:
        await self._get_owned(user_id, expense_id)
        await self._repo.delete(expense_id)

    async def summary(self, user_id: str, itinerary_id: str) -> ExpenseSummaryResponse:
        itinerary = await self._assert_itinerary_owned(user_id, itinerary_id)
        expenses = await self._repo.find_by_itinerary(itinerary_id)

        total_estimated = sum(
            (parse_estimated_cost(d.estimated_cost) or 0.0) for d in itinerary.destinations
        )
        total_real = sum(e.amount for e in expenses)
        difference = round(total_real - total_estimated, 2)

        if abs(difference) < 0.01:
            status = "on_budget"
        elif difference > 0:
            status = "over_budget"
        else:
            status = "under_budget"

        by_category: dict[str, float] = {}
        for e in expenses:
            by_category[e.category.value] = round(
                by_category.get(e.category.value, 0.0) + e.amount, 2
            )

        currency = expenses[0].currency if expenses else "USD"

        return ExpenseSummaryResponse(
            itinerary_id=itinerary_id,
            currency=currency,
            total_estimated=round(total_estimated, 2),
            total_real=round(total_real, 2),
            difference=difference,
            status=status,
            expenses_count=len(expenses),
            by_category=[
                CategoryBreakdown(category=cat, total=total)
                for cat, total in sorted(by_category.items())
            ],
        )

    async def _assert_itinerary_owned(self, user_id: str, itinerary_id: str):
        itinerary = await self._itinerary_repo.find_by_id(itinerary_id)
        if not itinerary:
            raise NotFoundError("Itinerary")
        if itinerary.user_id != user_id:
            raise ForbiddenError()
        return itinerary

    async def _get_owned(self, user_id: str, expense_id: str) -> Expense:
        expense = await self._repo.find_by_id(expense_id)
        if not expense:
            raise NotFoundError("Expense")
        if expense.user_id != user_id:
            raise ForbiddenError()
        return expense


def parse_estimated_cost(text: Optional[str]) -> Optional[float]:
    """
    Extrae un valor numérico aproximado de estimaciones como "$300-$500".
    Devuelve el punto medio del rango, o None si no hay números.
    """
    if not text:
        return None
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    values = [float(n.replace(",", "")) for n in numbers]
    if not values:
        return None
    return sum(values) / len(values)
