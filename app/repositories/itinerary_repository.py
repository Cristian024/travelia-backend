from typing import Optional

import asyncpg

from app.models.itinerary import (
    Activity,
    Destination,
    DestinationReplacement,
    ItineraryDocument,
    ReplacementStatus,
)
from app.models.planning import QuestionTree
from app.repositories import base
from app.repositories.base import BaseRepository, new_id

_DESTINATION_COLUMNS = (
    "destination_id", "position", "name", "country", "city", "days_allocated",
    "description", "transportation", "estimated_cost", "replacement_status", "replacement_tree_id",
)


class ItineraryRepository(BaseRepository[ItineraryDocument]):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, ItineraryDocument)

    async def insert(self, itinerary: ItineraryDocument) -> str:
        itinerary_id = new_id()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO itineraries (
                        id, user_id, planning_id, title, summary, arrival_date,
                        departure_date, total_days, status, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    itinerary_id, itinerary.user_id, itinerary.planning_id,
                    itinerary.title, itinerary.summary, itinerary.arrival_date,
                    itinerary.departure_date, itinerary.total_days,
                    itinerary.status.value, itinerary.created_at, itinerary.updated_at,
                )
                await self._insert_destinations(conn, itinerary_id, itinerary.destinations)
        return itinerary_id

    async def find_by_id(self, id_str: str) -> Optional[ItineraryDocument]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM itineraries WHERE id = $1", id_str)
            if not row:
                return None
            destinations = await self._load_destinations(conn, id_str)
        return self._to_document(row, destinations)

    async def find_by_user(self, user_id: str) -> list[ItineraryDocument]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM itineraries WHERE user_id = $1 ORDER BY created_at DESC",
                user_id,
            )
            documents = []
            for row in rows:
                destinations = await self._load_destinations(conn, row["id"], include_trees=False)
                documents.append(self._to_document(row, destinations))
        return documents

    async def find_by_planning(self, planning_id: str) -> list[ItineraryDocument]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM itineraries WHERE planning_id = $1 ORDER BY created_at DESC",
                planning_id,
            )
            documents = []
            for row in rows:
                destinations = await self._load_destinations(conn, row["id"])
                documents.append(self._to_document(row, destinations))
        return documents

    async def save(self, itinerary: ItineraryDocument) -> bool:
        if not itinerary.id:
            raise ValueError("Itinerary has no id")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                replaced_rows = await conn.fetch(
                    "SELECT replacement_tree_id FROM destinations WHERE itinerary_id = $1",
                    itinerary.id,
                )
                removed_tree_ids = {
                    r["replacement_tree_id"] for r in replaced_rows if r["replacement_tree_id"]
                }
                result = await conn.execute(
                    """
                    UPDATE itineraries SET
                        user_id = $2, planning_id = $3, title = $4, summary = $5,
                        arrival_date = $6, departure_date = $7, total_days = $8,
                        status = $9, created_at = $10, updated_at = $11
                    WHERE id = $1
                    """,
                    itinerary.id, itinerary.user_id, itinerary.planning_id,
                    itinerary.title, itinerary.summary, itinerary.arrival_date,
                    itinerary.departure_date, itinerary.total_days,
                    itinerary.status.value, itinerary.created_at, itinerary.updated_at,
                )
                if result.split()[-1] == "0":
                    return False
                await conn.execute("DELETE FROM destinations WHERE itinerary_id = $1", itinerary.id)
                new_tree_ids = await self._insert_destinations(conn, itinerary.id, itinerary.destinations)
                for tree_id in removed_tree_ids - new_tree_ids:
                    await base.delete_tree(conn, tree_id)
        return True

    async def create_indexes(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS itineraries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                planning_id TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                arrival_date TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                total_days INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_itineraries_user_id ON itineraries(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_itineraries_planning_id ON itineraries(planning_id)",
            """
            CREATE TABLE IF NOT EXISTS destinations (
                itinerary_id TEXT NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
                destination_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT NOT NULL,
                days_allocated INTEGER NOT NULL,
                description TEXT NOT NULL,
                transportation TEXT NOT NULL DEFAULT '',
                estimated_cost TEXT,
                replacement_status TEXT NOT NULL DEFAULT 'none',
                replacement_tree_id TEXT REFERENCES question_trees(id),
                PRIMARY KEY (itinerary_id, destination_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS destination_highlights (
                itinerary_id TEXT NOT NULL,
                destination_id TEXT NOT NULL,
                highlight TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (itinerary_id, destination_id, position),
                FOREIGN KEY (itinerary_id, destination_id)
                    REFERENCES destinations(itinerary_id, destination_id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS destination_accommodations (
                itinerary_id TEXT NOT NULL,
                destination_id TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (itinerary_id, destination_id, position),
                FOREIGN KEY (itinerary_id, destination_id)
                    REFERENCES destinations(itinerary_id, destination_id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS activities (
                itinerary_id TEXT NOT NULL,
                destination_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                duration_hours DOUBLE PRECISION NOT NULL,
                category TEXT NOT NULL,
                estimated_cost TEXT,
                PRIMARY KEY (itinerary_id, destination_id, activity_id),
                FOREIGN KEY (itinerary_id, destination_id)
                    REFERENCES destinations(itinerary_id, destination_id) ON DELETE CASCADE
            )
            """,
        ]
        for statement in statements:
            await self._pool.execute(statement)

    # --- Helpers ---

    async def _insert_destinations(
        self, conn: asyncpg.Connection, itinerary_id: str, destinations: list[Destination]
    ) -> set[str]:
        """Inserts all destinations (children first via their own inserts).
        Returns the set of replacement tree ids created."""
        new_tree_ids: set[str] = set()
        for dest in destinations:
            replacement_tree_id = None
            if dest.replacement.status != ReplacementStatus.none or dest.replacement.tree.nodes:
                replacement_tree_id = await base.create_tree(conn, dest.replacement.tree)
                new_tree_ids.add(replacement_tree_id)
            await conn.execute(
                """
                INSERT INTO destinations (
                    itinerary_id, destination_id, position, name, country, city,
                    days_allocated, description, transportation, estimated_cost,
                    replacement_status, replacement_tree_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                itinerary_id, dest.destination_id, dest.order, dest.name, dest.country,
                dest.city, dest.days_allocated, dest.description, dest.transportation,
                dest.estimated_cost, dest.replacement.status.value, replacement_tree_id,
            )
            for pos, highlight in enumerate(dest.highlights):
                await conn.execute(
                    """
                    INSERT INTO destination_highlights (itinerary_id, destination_id, highlight, position)
                    VALUES ($1, $2, $3, $4)
                    """,
                    itinerary_id, dest.destination_id, highlight, pos,
                )
            for pos, suggestion in enumerate(dest.accommodation_suggestions):
                await conn.execute(
                    """
                    INSERT INTO destination_accommodations (itinerary_id, destination_id, suggestion, position)
                    VALUES ($1, $2, $3, $4)
                    """,
                    itinerary_id, dest.destination_id, suggestion, pos,
                )
            for pos, activity in enumerate(dest.activities):
                await conn.execute(
                    """
                    INSERT INTO activities (
                        itinerary_id, destination_id, activity_id, position, name,
                        description, duration_hours, category, estimated_cost
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    itinerary_id, dest.destination_id, activity.activity_id, pos,
                    activity.name, activity.description, activity.duration_hours,
                    activity.category, activity.estimated_cost,
                )
        return new_tree_ids

    async def _load_destinations(
        self,
        conn: asyncpg.Connection,
        itinerary_id: str,
        include_trees: bool = True,
    ) -> list[Destination]:
        dest_rows = await conn.fetch(
            "SELECT * FROM destinations WHERE itinerary_id = $1 ORDER BY position",
            itinerary_id,
        )
        highlight_rows = await conn.fetch(
            "SELECT * FROM destination_highlights WHERE itinerary_id = $1 ORDER BY position",
            itinerary_id,
        )
        accommodation_rows = await conn.fetch(
            "SELECT * FROM destination_accommodations WHERE itinerary_id = $1 ORDER BY position",
            itinerary_id,
        )
        activity_rows = await conn.fetch(
            "SELECT * FROM activities WHERE itinerary_id = $1 ORDER BY position",
            itinerary_id,
        )

        highlights_by_dest: dict[str, list[str]] = {}
        for row in highlight_rows:
            highlights_by_dest.setdefault(row["destination_id"], []).append(row["highlight"])

        accommodations_by_dest: dict[str, list[str]] = {}
        for row in accommodation_rows:
            accommodations_by_dest.setdefault(row["destination_id"], []).append(row["suggestion"])

        activities_by_dest: dict[str, list[Activity]] = {}
        for row in activity_rows:
            activities_by_dest.setdefault(row["destination_id"], []).append(
                Activity(
                    activity_id=row["activity_id"],
                    name=row["name"],
                    description=row["description"],
                    duration_hours=row["duration_hours"],
                    category=row["category"],
                    estimated_cost=row["estimated_cost"],
                )
            )

        destinations: list[Destination] = []
        for row in dest_rows:
            tree = QuestionTree()
            if include_trees and row["replacement_tree_id"]:
                tree = await base.load_tree(conn, row["replacement_tree_id"])
            destinations.append(
                Destination(
                    destination_id=row["destination_id"],
                    order=row["position"],
                    name=row["name"],
                    country=row["country"],
                    city=row["city"],
                    days_allocated=row["days_allocated"],
                    description=row["description"],
                    highlights=highlights_by_dest.get(row["destination_id"], []),
                    accommodation_suggestions=accommodations_by_dest.get(row["destination_id"], []),
                    transportation=row["transportation"],
                    estimated_cost=row["estimated_cost"],
                    activities=activities_by_dest.get(row["destination_id"], []),
                    replacement=DestinationReplacement(
                        status=ReplacementStatus(row["replacement_status"]),
                        tree=tree,
                    ),
                )
            )
        return destinations

    def _to_document(
        self, row: asyncpg.Record, destinations: list[Destination]
    ) -> ItineraryDocument:
        data = dict(row)
        data["_id"] = data.pop("id")
        return ItineraryDocument(**{**data, "destinations": destinations})
