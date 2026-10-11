from datetime import datetime
from typing import Optional

import asyncpg

from app.models.plan import Plan
from app.ports.repositories import PlanRepositoryPort
from app.repositories.base import BaseRepository, new_id

_COLUMNS = (
    "id, code, name, amount_in_cents, currency, duration_days, is_active,"
    " created_at, updated_at"
)


class PlanRepository(BaseRepository[Plan], PlanRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, Plan)

    async def find_by_code(self, code: str) -> Optional[Plan]:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM plans WHERE code = $1", code.upper()
        )
        return self._to_model(row)

    async def find_by_id(self, plan_id: str) -> Optional[Plan]:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM plans WHERE id = $1", plan_id
        )
        return self._to_model(row)

    async def delete(self, plan_id: str) -> bool:
        result = await self._pool.execute("DELETE FROM plans WHERE id = $1", plan_id)
        return result.split()[-1] != "0"

    async def list_all(self) -> list[Plan]:
        rows = await self._pool.fetch(f"SELECT {_COLUMNS} FROM plans ORDER BY amount_in_cents")
        return [self._to_model(r) for r in rows]

    async def upsert(self, plan: Plan) -> str:
        existing_id = await self._pool.fetchval(
            "SELECT id FROM plans WHERE code = $1", plan.code.upper()
        )
        if existing_id:
            await self._pool.execute(
                """
                UPDATE plans SET name = $2, amount_in_cents = $3, currency = $4,
                    duration_days = $5, is_active = $6, updated_at = $7
                WHERE id = $1
                """,
                existing_id, plan.name, plan.amount_in_cents, plan.currency,
                plan.duration_days, plan.is_active, datetime.utcnow(),
            )
            return existing_id

        plan_id = new_id()
        await self._pool.execute(
            """
            INSERT INTO plans (id, code, name, amount_in_cents, currency,
                               duration_days, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            plan_id, plan.code.upper(), plan.name, plan.amount_in_cents,
            plan.currency, plan.duration_days, plan.is_active,
            plan.created_at, plan.updated_at,
        )
        return plan_id

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                amount_in_cents INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                duration_days INTEGER NOT NULL DEFAULT 30,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        # Bootstrap: planes iniciales (editables en BD).
        await self._pool.execute(
            """
            INSERT INTO plans (id, code, name, amount_in_cents, currency,
                               duration_days, is_active, created_at, updated_at)
            VALUES ('plan_free', 'FREE', 'Plan Free', 0, 'COP', 0, TRUE, NOW(), NOW()),
                   ('plan_premium', 'PREMIUM', 'Plan Premium', 4990000, 'COP', 30, TRUE, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
            """
        )

    def _to_model(self, row: Optional[asyncpg.Record]) -> Optional[Plan]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        return Plan(**data)
