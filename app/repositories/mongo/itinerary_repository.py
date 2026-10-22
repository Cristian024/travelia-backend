from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.itinerary import ItineraryDocument
from app.ports.repositories import ItineraryRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoItineraryRepository(MongoRepository[ItineraryDocument], ItineraryRepositoryPort):
    collection_name = "itineraries"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, ItineraryDocument)

    async def insert(self, itinerary: ItineraryDocument) -> str:
        itinerary_id = itinerary.id or new_id()
        itinerary.id = itinerary_id
        doc = self._to_doc(itinerary)
        doc["_id"] = itinerary_id
        await self._col.insert_one(doc)
        return itinerary_id

    async def find_by_id(self, id_str: str) -> Optional[ItineraryDocument]:
        return self._to_model(await self._col.find_one({"_id": id_str}))

    async def find_by_user(self, user_id: str) -> list[ItineraryDocument]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [self._to_model(doc) async for doc in cursor]

    async def find_by_planning(self, planning_id: str) -> list[ItineraryDocument]:
        cursor = self._col.find({"planning_id": planning_id}).sort("created_at", -1)
        return [self._to_model(doc) async for doc in cursor]

    async def find_public(
        self, user_id: str, limit: int, offset: int
    ) -> list[ItineraryDocument]:
        cursor = (
            self._col.find({"is_public": True, "user_id": {"$ne": user_id}})
            .sort("created_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return [self._to_model(doc) async for doc in cursor]

    async def count_public(self, user_id: str) -> int:
        return await self._col.count_documents(
            {"is_public": True, "user_id": {"$ne": user_id}}
        )

    async def set_public(self, itinerary_id: str, is_public: bool) -> bool:
        result = await self._col.update_one(
            {"_id": itinerary_id},
            {"$set": {"is_public": is_public, "updated_at": datetime.utcnow()}},
        )
        return result.matched_count > 0

    async def save(self, itinerary: ItineraryDocument) -> bool:
        if not itinerary.id:
            raise ValueError("Itinerary has no id")
        doc = self._to_doc(itinerary)
        result = await self._col.replace_one({"_id": itinerary.id}, doc)
        return result.matched_count > 0

    async def delete(self, itinerary_id: str) -> bool:
        result = await self._col.delete_one({"_id": itinerary_id})
        return result.deleted_count > 0

    async def create_indexes(self) -> None:
        await self._col.create_index("user_id")
        await self._col.create_index("planning_id")
        await self._col.create_index([("is_public", 1), ("created_at", -1)])
