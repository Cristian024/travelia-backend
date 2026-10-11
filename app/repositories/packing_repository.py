from typing import Optional

import asyncpg

from app.models.packing import PackingItem, PackingList
from app.ports.repositories import PackingListRepositoryPort
from app.repositories.base import BaseRepository, new_id


class PackingListRepository(BaseRepository[PackingList], PackingListRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, PackingList)

    async def upsert(self, packing_list: PackingList) -> str:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                existing_id = await conn.fetchval(
                    "SELECT id FROM packing_lists WHERE itinerary_id = $1",
                    packing_list.itinerary_id,
                )
                if existing_id:
                    list_id = existing_id
                    await conn.execute(
                        """
                        UPDATE packing_lists
                        SET destination_summary = $2, weather_summary = $3,
                            notes = $4, updated_at = $5
                        WHERE id = $1
                        """,
                        list_id,
                        packing_list.destination_summary,
                        packing_list.weather_summary,
                        packing_list.notes,
                        packing_list.updated_at,
                    )
                    await conn.execute(
                        "DELETE FROM packing_items WHERE packing_list_id = $1", list_id
                    )
                else:
                    list_id = new_id()
                    await conn.execute(
                        """
                        INSERT INTO packing_lists (
                            id, itinerary_id, destination_summary, weather_summary,
                            notes, created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        list_id,
                        packing_list.itinerary_id,
                        packing_list.destination_summary,
                        packing_list.weather_summary,
                        packing_list.notes,
                        packing_list.created_at,
                        packing_list.updated_at,
                    )

                for position, item in enumerate(packing_list.items):
                    await conn.execute(
                        """
                        INSERT INTO packing_items (
                            packing_list_id, position, category, item, quantity,
                            reason, checked
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        list_id, position, item.category, item.item,
                        item.quantity, item.reason, item.checked,
                    )
        return list_id

    async def find_by_itinerary(self, itinerary_id: str) -> Optional[PackingList]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM packing_lists WHERE itinerary_id = $1", itinerary_id
            )
            if not row:
                return None
            item_rows = await conn.fetch(
                "SELECT * FROM packing_items WHERE packing_list_id = $1 ORDER BY position",
                row["id"],
            )
        return self._to_model(row, item_rows)

    async def delete_by_itinerary(self, itinerary_id: str) -> bool:
        result = await self._pool.execute(
            "DELETE FROM packing_lists WHERE itinerary_id = $1", itinerary_id
        )
        return result.split()[-1] != "0"

    async def set_item_checked(
        self, itinerary_id: str, position: int, checked: bool
    ) -> bool:
        result = await self._pool.execute(
            """
            UPDATE packing_items i
            SET checked = $3
            FROM packing_lists l
            WHERE i.packing_list_id = l.id
              AND l.itinerary_id = $1
              AND i.position = $2
            """,
            itinerary_id, position, checked,
        )
        return result.split()[-1] != "0"

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS packing_lists (
                id TEXT PRIMARY KEY,
                itinerary_id TEXT NOT NULL UNIQUE REFERENCES itineraries(id) ON DELETE CASCADE,
                destination_summary TEXT NOT NULL DEFAULT '',
                weather_summary TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_packing_lists_itinerary_id ON packing_lists(itinerary_id)"
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS packing_items (
                packing_list_id TEXT NOT NULL REFERENCES packing_lists(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                quantity TEXT,
                reason TEXT,
                checked BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (packing_list_id, position)
            )
            """
        )

    def _to_model(
        self, row: asyncpg.Record, item_rows: list[asyncpg.Record]
    ) -> PackingList:
        data = dict(row)
        data["_id"] = data.pop("id")
        data["items"] = [
            PackingItem(
                category=r["category"],
                item=r["item"],
                quantity=r["quantity"],
                reason=r["reason"],
                checked=r["checked"],
            )
            for r in item_rows
        ]
        return PackingList(**data)
