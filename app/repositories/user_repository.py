from datetime import datetime
from typing import Optional

import asyncpg

from app.models.plan import PlanCode
from app.models.user import UserDocument, UserRole
from app.ports.repositories import UserRepositoryPort
from app.repositories.base import BaseRepository, new_id

_CLIENT_COLUMNS = (
    "id, email, hashed_password, full_name, birth_date, country_of_residence,"
    " phone, preferred_language, subscription_type, premium_since, is_active,"
    " created_at, updated_at"
)
_ADMIN_COLUMNS = "id, email, hashed_password, full_name, is_active, created_at, updated_at"

_UPDATABLE_CLIENT = {
    "email", "hashed_password", "full_name", "birth_date", "country_of_residence",
    "phone", "preferred_language", "subscription_type", "premium_since",
    "is_active", "updated_at",
}
_UPDATABLE_ADMIN = {"email", "hashed_password", "full_name", "is_active", "updated_at"}


class UserRepository(BaseRepository[UserDocument], UserRepositoryPort):
    """
    Facade de cuentas sobre dos tablas separadas (`clients` y `admins`).

    Mantiene el contrato `UserRepositoryPort` para no cambiar los servicios,
    pero el almacenamiento físico está dividido por rol.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, UserDocument)

    # --- Lectura ---

    async def find_by_id(self, id_str: str) -> Optional[UserDocument]:
        client_row = await self._pool.fetchrow(
            f"SELECT {_CLIENT_COLUMNS} FROM clients WHERE id = $1", id_str
        )
        if client_row:
            return self._client_to_model(client_row)
        admin_row = await self._pool.fetchrow(
            f"SELECT {_ADMIN_COLUMNS} FROM admins WHERE id = $1", id_str
        )
        return self._admin_to_model(admin_row)

    async def find_by_email(self, email: str) -> Optional[UserDocument]:
        email = email.lower()
        client_row = await self._pool.fetchrow(
            f"SELECT {_CLIENT_COLUMNS} FROM clients WHERE email = $1", email
        )
        if client_row:
            return self._client_to_model(client_row)
        admin_row = await self._pool.fetchrow(
            f"SELECT {_ADMIN_COLUMNS} FROM admins WHERE email = $1", email
        )
        return self._admin_to_model(admin_row)

    async def email_exists(self, email: str) -> bool:
        return await self._pool.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM clients WHERE email = $1)
                OR EXISTS(SELECT 1 FROM admins WHERE email = $1)
            """,
            email.lower(),
        )

    # --- Escritura ---

    async def insert(self, user: UserDocument) -> str:
        user_id = new_id()
        if user.role == UserRole.admin:
            await self._pool.execute(
                """
                INSERT INTO admins (id, email, hashed_password, full_name, is_active,
                                    created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id, user.email, user.hashed_password, user.full_name,
                user.is_active, user.created_at, user.updated_at,
            )
        else:
            await self._pool.execute(
                """
                INSERT INTO clients (id, email, hashed_password, full_name, birth_date,
                                     country_of_residence, phone, preferred_language,
                                     subscription_type, premium_since, is_active,
                                     created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                user_id, user.email, user.hashed_password, user.full_name,
                user.birth_date, user.country_of_residence, user.phone,
                user.preferred_language, user.subscription_type, user.premium_since,
                user.is_active, user.created_at, user.updated_at,
            )
        return user_id

    async def update_by_id(self, id_str: str, update_data: dict) -> bool:
        data = dict(update_data)
        role_raw = data.pop("role", None)
        new_role = (
            str(getattr(role_raw, "value", role_raw)).upper() if role_raw is not None else None
        )

        client_row = await self._pool.fetchrow("SELECT * FROM clients WHERE id = $1", id_str)
        admin_row = await self._pool.fetchrow("SELECT * FROM admins WHERE id = $1", id_str)

        if new_role == UserRole.admin.value and client_row and not admin_row:
            await self._move_client_to_admin(client_row, data)
            return True
        if new_role == UserRole.user.value and admin_row and not client_row:
            await self._move_admin_to_client(admin_row, data)
            return True

        if client_row:
            return await self._update_table("clients", id_str, data, _UPDATABLE_CLIENT)
        if admin_row:
            return await self._update_table("admins", id_str, data, _UPDATABLE_ADMIN)
        return False

    async def activate_premium(self, id_str: str) -> bool:
        now = datetime.utcnow()
        result = await self._pool.execute(
            """
            UPDATE clients
            SET subscription_type = $2, premium_since = $3, updated_at = $3
            WHERE id = $1
            """,
            id_str, PlanCode.PREMIUM, now,
        )
        return result.split()[-1] != "0"

    # --- Listado (clientes + administradores) ---

    async def list_all(self, limit: int, offset: int) -> list[UserDocument]:
        rows = await self._pool.fetch(
            """
            SELECT id, email, hashed_password, full_name, birth_date,
                   country_of_residence, phone, preferred_language, subscription_type,
                   premium_since, is_active, created_at, updated_at, 'USER' AS role
            FROM clients
            UNION ALL
            SELECT id, email, hashed_password, full_name, '' AS birth_date,
                   '' AS country_of_residence, NULL AS phone, 'es' AS preferred_language,
                   'FREE' AS subscription_type, NULL AS premium_since, is_active,
                   created_at, updated_at, 'ADMIN' AS role
            FROM admins
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
        return [self._row_to_model(r) for r in rows]

    async def count_all(self) -> int:
        return await self._pool.fetchval(
            "SELECT (SELECT COUNT(*) FROM clients) + (SELECT COUNT(*) FROM admins)"
        )

    # --- Esquema ---

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                country_of_residence TEXT NOT NULL,
                phone TEXT,
                preferred_language TEXT NOT NULL DEFAULT 'es',
                subscription_type TEXT NOT NULL DEFAULT 'FREE' REFERENCES plans(code),
                premium_since TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_clients_subscription ON clients(subscription_type)"
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_admins_email ON admins(email)"
        )

    # --- Helpers ---

    async def _update_table(self, table: str, id_str: str, data: dict, allowed: set) -> bool:
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return False
        assignments = ", ".join(f"{col} = ${i}" for i, col in enumerate(updates, start=2))
        result = await self._pool.execute(
            f"UPDATE {table} SET {assignments} WHERE id = $1",
            id_str, *updates.values(),
        )
        return result.split()[-1] != "0"

    async def _move_client_to_admin(self, client_row: asyncpg.Record, extra: dict) -> None:
        now = extra.get("updated_at", datetime.utcnow())
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO admins (id, email, hashed_password, full_name, is_active,
                                        created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    client_row["id"],
                    extra.get("email", client_row["email"]),
                    extra.get("hashed_password", client_row["hashed_password"]),
                    extra.get("full_name", client_row["full_name"]),
                    extra.get("is_active", client_row["is_active"]),
                    client_row["created_at"], now,
                )
                await conn.execute("DELETE FROM clients WHERE id = $1", client_row["id"])

    async def _move_admin_to_client(self, admin_row: asyncpg.Record, extra: dict) -> None:
        now = extra.get("updated_at", datetime.utcnow())
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO clients (id, email, hashed_password, full_name, birth_date,
                                         country_of_residence, phone, preferred_language,
                                         subscription_type, premium_since, is_active,
                                         created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    admin_row["id"],
                    extra.get("email", admin_row["email"]),
                    extra.get("hashed_password", admin_row["hashed_password"]),
                    extra.get("full_name", admin_row["full_name"]),
                    extra.get("birth_date", ""),
                    extra.get("country_of_residence", ""),
                    extra.get("phone"),
                    extra.get("preferred_language", "es"),
                    extra.get("subscription_type", PlanCode.FREE),
                    extra.get("premium_since"),
                    extra.get("is_active", admin_row["is_active"]),
                    admin_row["created_at"], now,
                )
                await conn.execute("DELETE FROM admins WHERE id = $1", admin_row["id"])

    def _client_to_model(self, row: Optional[asyncpg.Record]) -> Optional[UserDocument]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
        data["role"] = UserRole.user.value
        return UserDocument(**data)

    def _admin_to_model(self, row: Optional[asyncpg.Record]) -> Optional[UserDocument]:
        if not row:
            return None
        data = dict(row)
        data["_id"] = data.pop("id")
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

    def _row_to_model(self, row: asyncpg.Record) -> UserDocument:
        data = dict(row)
        data["_id"] = data.pop("id")
        return UserDocument(**data)
