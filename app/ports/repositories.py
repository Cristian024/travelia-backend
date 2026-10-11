"""
Puertos (Ports) de persistencia de la Arquitectura Hexagonal.

Los servicios dependen EXCLUSIVAMENTE de estas abstracciones, nunca de los
adaptadores concretos (asyncpg). Los repositorios en `app/repositories` son
los adaptadores que implementan estos contratos.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.models.expense import Expense
from app.models.itinerary import ItineraryDocument
from app.models.packing import PackingList
from app.models.planning import PlanningDocument
from app.models.user import UserDocument


class UserRepositoryPort(ABC):
    @abstractmethod
    async def find_by_id(self, id_str: str) -> Optional[UserDocument]: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[UserDocument]: ...

    @abstractmethod
    async def email_exists(self, email: str) -> bool: ...

    @abstractmethod
    async def insert(self, user: UserDocument) -> str: ...

    @abstractmethod
    async def update_by_id(self, id_str: str, update_data: dict) -> bool: ...


class PlanningRepositoryPort(ABC):
    @abstractmethod
    async def insert(self, planning: PlanningDocument) -> str: ...

    @abstractmethod
    async def find_by_id(self, id_str: str) -> Optional[PlanningDocument]: ...

    @abstractmethod
    async def find_by_user(self, user_id: str) -> list[PlanningDocument]: ...

    @abstractmethod
    async def save(self, planning: PlanningDocument) -> bool: ...

    @abstractmethod
    async def count_by_user_since(self, user_id: str, since: datetime) -> int: ...


class ItineraryRepositoryPort(ABC):
    @abstractmethod
    async def insert(self, itinerary: ItineraryDocument) -> str: ...

    @abstractmethod
    async def find_by_id(self, id_str: str) -> Optional[ItineraryDocument]: ...

    @abstractmethod
    async def find_by_user(self, user_id: str) -> list[ItineraryDocument]: ...

    @abstractmethod
    async def find_by_planning(self, planning_id: str) -> list[ItineraryDocument]: ...

    @abstractmethod
    async def save(self, itinerary: ItineraryDocument) -> bool: ...

    @abstractmethod
    async def delete(self, itinerary_id: str) -> bool: ...

    @abstractmethod
    async def find_public(
        self, user_id: str, limit: int, offset: int
    ) -> list[ItineraryDocument]: ...

    @abstractmethod
    async def count_public(
        self, user_id: str
    ) -> int: ...

    @abstractmethod
    async def set_public(self, itinerary_id: str, is_public: bool) -> bool: ...


class ExpenseRepositoryPort(ABC):
    @abstractmethod
    async def insert(self, expense: Expense) -> str: ...

    @abstractmethod
    async def find_by_id(self, expense_id: str) -> Optional[Expense]: ...

    @abstractmethod
    async def find_by_itinerary(self, itinerary_id: str) -> list[Expense]: ...

    @abstractmethod
    async def update(self, expense: Expense) -> bool: ...

    @abstractmethod
    async def delete(self, expense_id: str) -> bool: ...


class PackingListRepositoryPort(ABC):
    @abstractmethod
    async def upsert(self, packing_list: PackingList) -> str: ...

    @abstractmethod
    async def find_by_itinerary(self, itinerary_id: str) -> Optional[PackingList]: ...

    @abstractmethod
    async def delete_by_itinerary(self, itinerary_id: str) -> bool: ...

    @abstractmethod
    async def set_item_checked(
        self, itinerary_id: str, position: int, checked: bool
    ) -> bool: ...
