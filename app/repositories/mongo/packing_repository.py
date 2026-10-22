from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.packing import PackingList
from app.ports.repositories import PackingListRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoPackingListRepository(MongoRepository[PackingList], PackingListRepositoryPort):
    collection_name = "packing_lists"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, PackingList)

    async def upsert(self, packing_list: PackingList) -> str:
        existing = await self._col.find_one({"itinerary_id": packing_list.itinerary_id})
        if existing:
            list_id = existing["_id"]
            packing_list.id = list_id
            doc = self._to_doc(packing_list)
            doc["_id"] = list_id
            await self._col.replace_one({"_id": list_id}, doc)
            return list_id

        list_id = packing_list.id or new_id()
        packing_list.id = list_id
        doc = self._to_doc(packing_list)
        doc["_id"] = list_id
        await self._col.insert_one(doc)
        return list_id

    async def find_by_itinerary(self, itinerary_id: str) -> Optional[PackingList]:
        return self._to_model(await self._col.find_one({"itinerary_id": itinerary_id}))

    async def delete_by_itinerary(self, itinerary_id: str) -> bool:
        result = await self._col.delete_one({"itinerary_id": itinerary_id})
        return result.deleted_count > 0

    async def set_item_checked(
        self, itinerary_id: str, position: int, checked: bool
    ) -> bool:
        result = await self._col.update_one(
            {"itinerary_id": itinerary_id, f"items.{position}": {"$exists": True}},
            {
                "$set": {
                    f"items.{position}.checked": checked,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        return result.matched_count > 0

    async def create_indexes(self) -> None:
        await self._col.create_index("itinerary_id", unique=True)
