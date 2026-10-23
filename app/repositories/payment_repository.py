from datetime import datetime
from typing import Optional

import asyncpg

from app.models.payment import Payment, PaymentStatus
from app.ports.repositories import PaymentRepositoryPort
from app.repositories.base import BaseRepository, new_id

_COLUMNS = (
    "id, order_id, user_id, reference, amount_in_cents, currency, status,"
    " transaction_id, created_at, updated_at"
)


class PaymentRepository(BaseRepository[Payment], PaymentRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, Payment)

    async def insert(self, payment: Payment) -> str:
        payment_id = new_id()
        await self._pool.execute(
            """
            INSERT INTO payments (id, order_id, user_id, reference, amount_in_cents,
                                  currency, status, transaction_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            payment_id, payment.order_id, payment.user_id, payment.reference,
            payment.amount_in_cents, payment.currency, payment.status.value,
            payment.transaction_id, payment.created_at, payment.updated_at,
        )
        return payment_id

    async def find_by_reference(self, reference: str) -> Optional[Payment]:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM payments WHERE reference = $1", reference
        )
        return self._to_model(row)

    async def find_by_id(self, payment_id: str) -> Optional[Payment]:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM payments WHERE id = $1", payment_id
        )
        return self._to_model(row)

    async def list_all(self, limit: int, offset: int) -> list[Payment]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM payments ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
        return [self._to_model(r) for r in rows]

    async def count_all(self) -> int:
        return await self._pool.fetchval("SELECT COUNT(*) FROM payments")

    async def update_status(
        self,
        reference: str,
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
    ) -> bool:
        result = await self._pool.execute(
            """
            UPDATE payments
            SET status = $2, transaction_id = $3, updated_at = $4
            WHERE reference = $1
            """,
            reference, status.value, transaction_id, datetime.utcnow(),
        )
        return result.split()[-1] != "0"

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                order_id TEXT REFERENCES orders(id),
                user_id TEXT NOT NULL,
                reference TEXT NOT NULL UNIQUE,
                amount_in_cents INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'COP',
                status TEXT NOT NULL DEFAULT 'PENDING',
                transaction_id TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)"
        )

    def _to_model(self, row: Optional[asyncpg.Record]) -> Optional[Payment]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        return Payment(**data)
