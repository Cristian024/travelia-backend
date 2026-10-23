from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.payment import Payment, PaymentStatus
from app.ports.repositories import PaymentRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoPaymentRepository(MongoRepository[Payment], PaymentRepositoryPort):
    collection_name = "payments"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Payment)

    async def insert(self, payment: Payment) -> str:
        payment_id = payment.id or new_id()
        payment.id = payment_id
        doc = self._to_doc(payment)
        doc["_id"] = payment_id
        await self._col.insert_one(doc)
        return payment_id

    async def find_by_reference(self, reference: str) -> Optional[Payment]:
        return self._to_model(await self._col.find_one({"reference": reference}))

    async def find_by_id(self, payment_id: str) -> Optional[Payment]:
        return self._to_model(await self._col.find_one({"_id": payment_id}))

    async def update_status(
        self,
        reference: str,
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
    ) -> bool:
        result = await self._col.update_one(
            {"reference": reference},
            {
                "$set": {
                    "status": status.value,
                    "transaction_id": transaction_id,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.matched_count > 0

    async def list_all(self, limit: int, offset: int) -> list[Payment]:
        cursor = self._col.find().sort("created_at", -1).skip(offset).limit(limit)
        return [self._to_model(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def create_indexes(self) -> None:
        await self._col.create_index("reference", unique=True)
        await self._col.create_index("user_id")
        await self._col.create_index("order_id")
