from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.expense import Expense
from app.ports.repositories import ExpenseRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository


class MongoExpenseRepository(MongoRepository[Expense], ExpenseRepositoryPort):
    collection_name = "expenses"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Expense)

    async def insert(self, expense: Expense) -> str:
        expense_id = expense.id or new_id()
        expense.id = expense_id
        doc = self._to_doc(expense)
        doc["_id"] = expense_id
        await self._col.insert_one(doc)
        return expense_id

    async def find_by_id(self, expense_id: str) -> Optional[Expense]:
        return self._to_model(await self._col.find_one({"_id": expense_id}))

    async def find_by_itinerary(self, itinerary_id: str) -> list[Expense]:
        cursor = (
            self._col.find({"itinerary_id": itinerary_id})
            .sort([("expense_date", 1), ("created_at", 1)])
        )
        return [self._to_model(doc) async for doc in cursor]

    async def update(self, expense: Expense) -> bool:
        if not expense.id:
            raise ValueError("Expense has no id")
        doc = self._to_doc(expense)
        result = await self._col.replace_one({"_id": expense.id}, doc)
        return result.matched_count > 0

    async def delete(self, expense_id: str) -> bool:
        result = await self._col.delete_one({"_id": expense_id})
        return result.deleted_count > 0

    async def create_indexes(self) -> None:
        await self._col.create_index("itinerary_id")
        await self._col.create_index("user_id")
