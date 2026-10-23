from datetime import datetime
from typing import Optional

import asyncpg

from app.models.order import Order, OrderStatus
from app.ports.repositories import OrderRepositoryPort
from app.repositories.base import BaseRepository, new_id

_COLUMNS = (
    "id, user_id, plan_code, amount_in_cents, currency, status, created_at, updated_at"
)


class OrderRepository(BaseRepository[Order], OrderRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, Order)

    async def insert(self, order: Order) -> str:
        order_id = new_id()
        await self._pool.execute(
            """
            INSERT INTO orders (id, user_id, plan_code, amount_in_cents, currency,
                                status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            order_id, order.user_id, order.plan_code, order.amount_in_cents,
            order.currency, order.status.value, order.created_at, order.updated_at,
        )
        return order_id

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM orders WHERE id = $1", order_id
        )
        return self._to_model(row)

    async def find_by_user(self, user_id: str) -> list[Order]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM orders WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [self._to_model(r) for r in rows]

    async def update_status(self, order_id: str, status: OrderStatus) -> bool:
        result = await self._pool.execute(
            "UPDATE orders SET status = $2, updated_at = $3 WHERE id = $1",
            order_id, status.value, datetime.utcnow(),
        )
        return result.split()[-1] != "0"

    async def list_all(self, limit: int, offset: int) -> list[Order]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM orders ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
        return [self._to_model(r) for r in rows]

    async def count_all(self) -> int:
        return await self._pool.fetchval("SELECT COUNT(*) FROM orders")

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                plan_code TEXT NOT NULL,
                amount_in_cents INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)"
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)"
        )

    def _to_model(self, row: Optional[asyncpg.Record]) -> Optional[Order]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        return Order(**data)
