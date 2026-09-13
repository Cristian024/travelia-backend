from typing import Optional

import asyncpg

from app.models.user import UserDocument
from app.repositories.base import BaseRepository, new_id

_COLUMNS = (
    "id, email, hashed_password, full_name, birth_date, country_of_residence,"
    " phone, preferred_language, created_at, updated_at"
)

_UPDATABLE_COLUMNS = {
    "email",
    "hashed_password",
    "full_name",
    "birth_date",
    "country_of_residence",
    "phone",
    "preferred_language",
    "updated_at",
}


class UserRepository(BaseRepository[UserDocument]):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, UserDocument)

    async def find_by_id(self, id_str: str) -> Optional[UserDocument]:
        row = await self._pool.fetchrow(f"SELECT {_COLUMNS} FROM users WHERE id = $1", id_str)
        return self._to_model(row)

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        row = await self._pool.fetchrow(f"SELECT {_COLUMNS} FROM users WHERE email = $1", email.lower())
        return self._to_model(row)

    async def email_exists(self, email: str) -> bool:
        return await self._pool.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)", email.lower())

    async def insert(self, user: UserDocument) -> str:
        user_id = new_id()
        await self._pool.execute(
            """
            INSERT INTO users (id, email, hashed_password, full_name, birth_date,
                               country_of_residence, phone, preferred_language,
                               created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            user_id, user.email, user.hashed_password, user.full_name, user.birth_date,
            user.country_of_residence, user.phone, user.preferred_language,
            user.created_at, user.updated_at,
        )
        return user_id

    async def update_by_id(self, id_str: str, update_data: dict) -> bool:
        updates = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
        if not updates:
            return False
        assignments = ", ".join(f"{col} = ${i}" for i, col in enumerate(updates, start=2))
        result = await self._pool.execute(
            f"UPDATE users SET {assignments} WHERE id = $1",
            id_str, *updates.values(),
        )
        return result.split()[-1] != "0"

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                country_of_residence TEXT NOT NULL,
                phone TEXT,
                preferred_language TEXT NOT NULL DEFAULT 'es',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )

    def _to_model(self, row: Optional[asyncpg.Record]) -> Optional[UserDocument]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        return UserDocument(**data)
