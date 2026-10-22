from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.plan import Plan
from app.ports.repositories import PlanRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoPlanRepository(MongoRepository[Plan], PlanRepositoryPort):
    collection_name = "plans"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Plan)

    async def find_by_code(self, code: str) -> Optional[Plan]:
        return self._to_model(await self._col.find_one({"code": code.upper()}))

    async def find_by_id(self, plan_id: str) -> Optional[Plan]:
        return self._to_model(await self._col.find_one({"_id": plan_id}))

    async def list_all(self) -> list[Plan]:
        cursor = self._col.find().sort("amount_in_cents", 1)
        return [self._to_model(doc) async for doc in cursor]

    async def upsert(self, plan: Plan) -> str:
        code = plan.code.upper()
        existing = await self._col.find_one({"code": code})
        if existing:
            plan.id = existing["_id"]
            plan.code = code
            plan.updated_at = datetime.utcnow()
            doc = self._to_doc(plan)
            doc["_id"] = existing["_id"]
            await self._col.replace_one({"_id": existing["_id"]}, doc)
            return existing["_id"]

        plan_id = plan.id or new_id()
        plan.id = plan_id
        plan.code = code
        doc = self._to_doc(plan)
        doc["_id"] = plan_id
        await self._col.insert_one(doc)
        return plan_id

    async def delete(self, plan_id: str) -> bool:
        result = await self._col.delete_one({"_id": plan_id})
        return result.deleted_count > 0

    async def create_indexes(self) -> None:
        await self._col.create_index("code", unique=True)
        defaults = [
            {"code": "FREE", "name": "Plan Free", "amount_in_cents": 0,
             "currency": "COP", "duration_days": 0},
            {"code": "PREMIUM", "name": "Plan Premium", "amount_in_cents": 4990000,
             "currency": "COP", "duration_days": 30},
        ]
        for data in defaults:
            if not await self._col.find_one({"code": data["code"]}):
                plan = Plan(id=new_id(), **data)
                doc = self._to_doc(plan)
                doc["_id"] = plan.id
                await self._col.insert_one(doc)
