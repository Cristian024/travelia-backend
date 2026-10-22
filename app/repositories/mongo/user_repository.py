from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.plan import PlanCode
from app.models.user import UserDocument
from app.ports.repositories import UserRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoUserRepository(MongoRepository[UserDocument], UserRepositoryPort):
    collection_name = "users"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, UserDocument)

    async def find_by_id(self, id_str: str) -> Optional[UserDocument]:
        return self._to_model(await self._col.find_one({"_id": id_str}))

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        return self._to_model(await self._col.find_one({"email": email.lower()}))

    async def email_exists(self, email: str) -> bool:
        return await self._col.count_documents({"email": email.lower()}, limit=1) > 0

    async def insert(self, user: UserDocument) -> str:
        user_id = user.id or new_id()
        user.id = user_id
        doc = self._to_doc(user)
        doc["_id"] = user_id
        await self._col.insert_one(doc)
        return user_id

    async def update_by_id(self, id_str: str, update_data: dict) -> bool:
        if not update_data:
            return False
        result = await self._col.update_one({"_id": id_str}, {"$set": update_data})
        return result.matched_count > 0

    async def activate_premium(self, id_str: str) -> bool:
        now = datetime.utcnow()
        result = await self._col.update_one(
            {"_id": id_str},
            {
                "$set": {
                    "subscription_type": PlanCode.PREMIUM,
                    "premium_since": now,
                    "updated_at": now,
                }
            },
        )
        return result.matched_count > 0

    async def list_all(self, limit: int, offset: int) -> list[UserDocument]:
        cursor = self._col.find().sort("created_at", -1).skip(offset).limit(limit)
        return [self._to_model(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    async def create_indexes(self) -> None:
        await self._col.create_index("email", unique=True)
        await self._col.create_index("subscription_type")
        await self._col.create_index("role")
