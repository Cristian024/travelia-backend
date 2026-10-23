from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.plan import PlanCode
from app.models.user import UserDocument, UserRole
from app.ports.repositories import UserRepositoryPort
from app.repositories.base import new_id
from app.repositories.mongo.base import MongoRepository

_CLIENT_FIELDS = {
    "email", "hashed_password", "full_name", "birth_date", "country_of_residence",
    "phone", "preferred_language", "subscription_type", "premium_since",
    "is_active", "updated_at",
}
_ADMIN_FIELDS = {"email", "hashed_password", "full_name", "is_active", "updated_at"}


class MongoUserRepository(MongoRepository[UserDocument], UserRepositoryPort):
    """Facade de cuentas sobre las colecciones `clients` y `admins`."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, UserDocument)

    @property
    def _clients(self):
        return self._db["clients"]

    @property
    def _admins(self):
        return self._db["admins"]

    async def find_by_id(self, id_str: str) -> Optional[UserDocument]:
        client = await self._clients.find_one({"_id": id_str})
        if client:
            return self._client_to_model(client)
        return self._admin_to_model(await self._admins.find_one({"_id": id_str}))

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        email = email.lower()
        client = await self._clients.find_one({"email": email})
        if client:
            return self._client_to_model(client)
        return self._admin_to_model(await self._admins.find_one({"email": email}))

    async def email_exists(self, email: str) -> bool:
        email = email.lower()
        clients = await self._clients.count_documents({"email": email}, limit=1)
        admins = await self._admins.count_documents({"email": email}, limit=1)
        return (clients + admins) > 0

    async def insert(self, user: UserDocument) -> str:
        user_id = user.id or new_id()
        user.id = user_id
        if user.role == UserRole.admin:
            doc = {
                "_id": user_id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
            await self._admins.insert_one(doc)
        else:
            doc = self._to_doc(user)
            doc["_id"] = user_id
            await self._clients.insert_one(doc)
        return user_id

    async def update_by_id(self, id_str: str, update_data: dict) -> bool:
        data = dict(update_data)
        role_raw = data.pop("role", None)
        new_role = (
            str(getattr(role_raw, "value", role_raw)).upper() if role_raw is not None else None
        )
        client = await self._clients.find_one({"_id": id_str})
        admin = await self._admins.find_one({"_id": id_str})

        if new_role == UserRole.admin.value and client and not admin:
            await self._move(client, "admins", data)
            return True
        if new_role == UserRole.user.value and admin and not client:
            await self._move(admin, "clients", data)
            return True
        if client:
            return await self._update("clients", id_str, data, _CLIENT_FIELDS)
        if admin:
            return await self._update("admins", id_str, data, _ADMIN_FIELDS)
        return False

    async def activate_premium(self, id_str: str) -> bool:
        now = datetime.utcnow()
        result = await self._clients.update_one(
            {"_id": id_str},
            {"$set": {"subscription_type": PlanCode.PREMIUM, "premium_since": now, "updated_at": now}},
        )
        return result.matched_count > 0

    async def list_all(self, limit: int, offset: int) -> list[UserDocument]:
        clients = [self._client_to_model(d) async for d in self._clients.find()]
        admins = [self._admin_to_model(d) async for d in self._admins.find()]
        users = clients + admins
        users.sort(key=lambda u: u.created_at, reverse=True)
        return users[offset: offset + limit]

    async def count_all(self) -> int:
        return (
            await self._clients.count_documents({})
            + await self._admins.count_documents({})
        )

    async def create_indexes(self) -> None:
        await self._clients.create_index("email", unique=True)
        await self._clients.create_index("subscription_type")
        await self._admins.create_index("email", unique=True)

    async def _update(self, collection: str, id_str: str, data: dict, allowed: set) -> bool:
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return False
        result = await self._db[collection].update_one({"_id": id_str}, {"$set": updates})
        return result.matched_count > 0

    async def _move(self, source_doc: dict, target: str, extra: dict) -> None:
        _id = source_doc["_id"]
        now = extra.get("updated_at", datetime.utcnow())
        if target == "admins":
            new_doc = {
                "_id": _id,
                "email": extra.get("email", source_doc.get("email")),
                "hashed_password": extra.get("hashed_password", source_doc.get("hashed_password")),
                "full_name": extra.get("full_name", source_doc.get("full_name")),
                "is_active": extra.get("is_active", source_doc.get("is_active", True)),
                "created_at": source_doc.get("created_at", now),
                "updated_at": now,
            }
            await self._admins.replace_one({"_id": _id}, new_doc, upsert=True)
            await self._clients.delete_one({"_id": _id})
        else:
            new_doc = {
                "_id": _id,
                "email": extra.get("email", source_doc.get("email")),
                "hashed_password": extra.get("hashed_password", source_doc.get("hashed_password")),
                "full_name": extra.get("full_name", source_doc.get("full_name")),
                "birth_date": extra.get("birth_date", source_doc.get("birth_date", "")),
                "country_of_residence": extra.get(
                    "country_of_residence", source_doc.get("country_of_residence", "")
                ),
                "phone": extra.get("phone", source_doc.get("phone")),
                "preferred_language": extra.get(
                    "preferred_language", source_doc.get("preferred_language", "es")
                ),
                "subscription_type": extra.get(
                    "subscription_type", source_doc.get("subscription_type", PlanCode.FREE)
                ),
                "premium_since": extra.get("premium_since", source_doc.get("premium_since")),
                "is_active": extra.get("is_active", source_doc.get("is_active", True)),
                "created_at": source_doc.get("created_at", now),
                "updated_at": now,
            }
            await self._clients.replace_one({"_id": _id}, new_doc, upsert=True)
            await self._admins.delete_one({"_id": _id})

    def _client_to_model(self, doc: Optional[dict]) -> Optional[UserDocument]:
        if not doc:
            return None
        data = dict(doc)
        data["role"] = UserRole.user.value
        return UserDocument(**data)

    def _admin_to_model(self, doc: Optional[dict]) -> Optional[UserDocument]:
        if not doc:
            return None
        data = dict(doc)
        data.update(
            {
                "birth_date": "",
                "country_of_residence": "",
                "phone": None,
                "preferred_language": "es",
                "subscription_type": PlanCode.FREE,
                "premium_since": None,
                "role": UserRole.admin.value,
            }
        )
        return UserDocument(**data)
