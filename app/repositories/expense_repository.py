from typing import Optional

import asyncpg

from app.models.expense import Expense
from app.ports.repositories import ExpenseRepositoryPort
from app.repositories.base import BaseRepository, new_id

_COLUMNS = (
    "id, itinerary_id, user_id, category, description, amount, currency,"
    " expense_date, created_at, updated_at"
)


class ExpenseRepository(BaseRepository[Expense], ExpenseRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, Expense)

    async def insert(self, expense: Expense) -> str:
        expense_id = new_id()
        await self._pool.execute(
            """
            INSERT INTO expenses (id, itinerary_id, user_id, category, description,
                                  amount, currency, expense_date, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            expense_id, expense.itinerary_id, expense.user_id,
            expense.category.value, expense.description, expense.amount,
            expense.currency, expense.expense_date,
            expense.created_at, expense.updated_at,
        )
        return expense_id

    async def find_by_id(self, expense_id: str) -> Optional[Expense]:
        row = await self._pool.fetchrow(f"SELECT {_COLUMNS} FROM expenses WHERE id = $1", expense_id)
        return self._to_model(row)

    async def find_by_itinerary(self, itinerary_id: str) -> list[Expense]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM expenses WHERE itinerary_id = $1 ORDER BY expense_date, created_at",
            itinerary_id,
        )
        return [self._to_model(row) for row in rows]

    async def update(self, expense: Expense) -> bool:
        if not expense.id:
            raise ValueError("Expense has no id")
        result = await self._pool.execute(
            """
            UPDATE expenses SET
                itinerary_id = $2, user_id = $3, category = $4, description = $5,
                amount = $6, currency = $7, expense_date = $8, updated_at = $9
            WHERE id = $1
            """,
            expense.id, expense.itinerary_id, expense.user_id,
            expense.category.value, expense.description, expense.amount,
            expense.currency, expense.expense_date, expense.updated_at,
        )
        return result.split()[-1] != "0"

    async def delete(self, expense_id: str) -> bool:
        result = await self._pool.execute("DELETE FROM expenses WHERE id = $1", expense_id)
        return result.split()[-1] != "0"

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                itinerary_id TEXT NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                amount NUMERIC(12, 2) NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                expense_date TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_itinerary_id ON expenses(itinerary_id)"
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)"
        )

    def _to_model(self, row: Optional[asyncpg.Record]) -> Optional[Expense]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        return Expense(**data)
