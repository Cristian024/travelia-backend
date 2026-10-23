from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.order import Order, OrderStatus
from app.ports.repositories import OrderRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoOrderRepository(MongoRepository[Order], OrderRepositoryPort):
    collection_name = "orders"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Order)

    async def insert(self, order: Order) -> str:
        order_id = order.id or new_id()
        order.id = order_id
        doc = self._to_doc(order)
        doc["_id"] = order_id
        await self._col.insert_one(doc)
        return order_id

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._to_model(await self._col.find_one({"_id": order_id}))

    async def find_by_user(self, user_id: str) -> list[Order]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [self._to_model(doc) async for doc in cursor]

    async def update_status(self, order_id: str, status: OrderStatus) -> bool:
        result = await self._col.update_one(
            {"_id": order_id},
            {"$set": {"status": status.value, "updated_at": datetime.utcnow()}},
        )
        return result.matched_count > 0

    async def list_all(self, limit: int, offset: int) -> list[Order]:
        cursor = self._col.find().sort("created_at", -1).skip(offset).limit(limit)
        return [self._to_model(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def create_indexes(self) -> None:
        await self._col.create_index("user_id")
        await self._col.create_index("status")
