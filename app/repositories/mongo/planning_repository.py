from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.planning import PlanningDocument
from app.ports.repositories import PlanningRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoPlanningRepository(MongoRepository[PlanningDocument], PlanningRepositoryPort):
    collection_name = "plannings"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, PlanningDocument)

    async def insert(self, planning: PlanningDocument) -> str:
        planning_id = planning.id or new_id()
        planning.id = planning_id
        doc = self._to_doc(planning)
        doc["_id"] = planning_id
        await self._col.insert_one(doc)
        return planning_id

    async def find_by_id(self, id_str: str) -> Optional[PlanningDocument]:
        return self._to_model(await self._col.find_one({"_id": id_str}))

    async def find_by_user(self, user_id: str) -> list[PlanningDocument]:
        cursor = self._col.find({"user_id": user_id}).sort("created_at", -1)
        return [self._to_model(doc) async for doc in cursor]

    async def save(self, planning: PlanningDocument) -> bool:
        if not planning.id:
            raise ValueError("Planning has no id")
        doc = self._to_doc(planning)
        result = await self._col.replace_one({"_id": planning.id}, doc)
        return result.matched_count > 0

    async def count_by_user_since(self, user_id: str, since: datetime) -> int:
        return await self._col.count_documents(
            {"user_id": user_id, "created_at": {"$gte": since}}
        )

    async def create_indexes(self) -> None:
        await self._col.create_index("user_id")
        await self._col.create_index([("user_id", 1), ("created_at", 1)])
