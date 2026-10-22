from typing import Generic, Optional, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class MongoRepository(Generic[T]):
    """Base para adaptadores MongoDB: un documento por agregado de dominio."""

    collection_name: str = ""

    def __init__(self, db: AsyncIOMotorDatabase, model_class: type[T]) -> None:
        self._db = db
        self._model = model_class

    @property
    def _col(self) -> AsyncIOMotorCollection:
        return self._db[self.collection_name]

    def _to_doc(self, model: T) -> dict:
        return model.model_dump(by_alias=True)

    def _to_model(self, doc: Optional[dict]) -> Optional[T]:
        if doc is None:
            return None
        return self._model(**dict(doc))

    async def create_indexes(self) -> None:
        """Cada adaptador define sus índices."""
        return None
