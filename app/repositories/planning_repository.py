from datetime import datetime
from typing import Optional

import asyncpg

from app.models.planning import GeneralAnswers, PlanningDocument, QuestionTree
from app.ports.repositories import PlanningRepositoryPort
from app.repositories import base
from app.repositories.base import BaseRepository, new_id

_GENERAL_ANSWER_FIELDS = (
    "destination_country", "destination_city", "arrival_date", "departure_date",
    "total_days", "number_of_travelers", "budget_range", "travel_purpose",
    "has_children", "special_requirements",
)


class PlanningRepository(BaseRepository[PlanningDocument], PlanningRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__(pool, PlanningDocument)

    async def insert(self, planning: PlanningDocument) -> str:
        planning_id = new_id()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                tree_id = await base.create_tree(conn, planning.tree)
                await conn.execute(
                    """
                    INSERT INTO plannings (
                        id, user_id, status,
                        destination_country, destination_city, arrival_date, departure_date,
                        total_days, number_of_travelers, budget_range, travel_purpose,
                        has_children, special_requirements,
                        tree_id, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    """,
                    planning_id, planning.user_id, planning.status.value,
                    planning.general_answers.destination_country,
                    planning.general_answers.destination_city,
                    planning.general_answers.arrival_date,
                    planning.general_answers.departure_date,
                    planning.general_answers.total_days,
                    planning.general_answers.number_of_travelers,
                    planning.general_answers.budget_range.value,
                    planning.general_answers.travel_purpose.value,
                    planning.general_answers.has_children,
                    planning.general_answers.special_requirements,
                    tree_id, planning.created_at, planning.updated_at,
                )
        return planning_id

    async def find_by_id(self, id_str: str) -> Optional[PlanningDocument]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM plannings WHERE id = $1", id_str)
            if not row:
                return None
            tree = await base.load_tree(conn, row["tree_id"])
        return self._to_document(row, tree)

    async def find_by_user(self, user_id: str) -> list[PlanningDocument]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM plannings WHERE user_id = $1 ORDER BY created_at DESC",
                user_id,
            )
            documents = []
            for row in rows:
                tree = await base.load_tree(conn, row["tree_id"])
                documents.append(self._to_document(row, tree))
        return documents

    async def count_by_user_since(self, user_id: str, since: datetime) -> int:
        return await self._pool.fetchval(
            "SELECT COUNT(*) FROM plannings WHERE user_id = $1 AND created_at >= $2",
            user_id,
            since,
        )

    async def save(self, planning: PlanningDocument) -> bool:
        if not planning.id:
            raise ValueError("Planning has no id")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("SELECT tree_id FROM plannings WHERE id = $1", planning.id)
                if not row:
                    return False
                await base.update_tree(conn, row["tree_id"], planning.tree)
                await conn.execute(
                    """
                    UPDATE plannings SET
                        status = $2,
                        destination_country = $3, destination_city = $4,
                        arrival_date = $5, departure_date = $6,
                        total_days = $7, number_of_travelers = $8,
                        budget_range = $9, travel_purpose = $10,
                        has_children = $11, special_requirements = $12,
                        created_at = $13, updated_at = $14
                    WHERE id = $1
                    """,
                    planning.id, planning.status.value,
                    planning.general_answers.destination_country,
                    planning.general_answers.destination_city,
                    planning.general_answers.arrival_date,
                    planning.general_answers.departure_date,
                    planning.general_answers.total_days,
                    planning.general_answers.number_of_travelers,
                    planning.general_answers.budget_range.value,
                    planning.general_answers.travel_purpose.value,
                    planning.general_answers.has_children,
                    planning.general_answers.special_requirements,
                    planning.created_at, planning.updated_at,
                )
        return True

    async def create_indexes(self) -> None:
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS question_trees (
                id TEXT PRIMARY KEY,
                root_id TEXT,
                current_node_id TEXT
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS question_nodes (
                node_id TEXT PRIMARY KEY,
                tree_id TEXT NOT NULL REFERENCES question_trees(id) ON DELETE CASCADE,
                parent_id TEXT REFERENCES question_nodes(node_id),
                depth INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                answered_at TIMESTAMP
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS node_questions (
                node_id TEXT NOT NULL REFERENCES question_nodes(node_id) ON DELETE CASCADE,
                question_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                required BOOLEAN NOT NULL DEFAULT TRUE,
                position INTEGER NOT NULL,
                PRIMARY KEY (node_id, question_id)
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS question_options (
                node_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                option_text TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (node_id, question_id, position),
                FOREIGN KEY (node_id, question_id)
                    REFERENCES node_questions(node_id, question_id) ON DELETE CASCADE
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS node_answers (
                node_id TEXT NOT NULL REFERENCES question_nodes(node_id) ON DELETE CASCADE,
                question_id TEXT NOT NULL,
                answer_type TEXT NOT NULL,
                answer_text TEXT,
                answer_number DOUBLE PRECISION,
                position INTEGER NOT NULL,
                PRIMARY KEY (node_id, question_id)
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS answer_items (
                node_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                item TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (node_id, question_id, position),
                FOREIGN KEY (node_id, question_id)
                    REFERENCES node_answers(node_id, question_id) ON DELETE CASCADE
            )
            """
        )
        await self._pool.execute(
            """
            CREATE TABLE IF NOT EXISTS plannings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                destination_country TEXT NOT NULL,
                destination_city TEXT,
                arrival_date TEXT NOT NULL,
                departure_date TEXT NOT NULL,
                total_days INTEGER NOT NULL,
                number_of_travelers INTEGER NOT NULL,
                budget_range TEXT NOT NULL,
                travel_purpose TEXT NOT NULL,
                has_children BOOLEAN NOT NULL DEFAULT FALSE,
                special_requirements TEXT,
                tree_id TEXT REFERENCES question_trees(id),
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
        await self._pool.execute("CREATE INDEX IF NOT EXISTS idx_plannings_user_id ON plannings(user_id)")
        await self._pool.execute(
            "CREATE INDEX IF NOT EXISTS idx_plannings_user_created ON plannings(user_id, created_at)"
        )

    def _to_document(self, row: asyncpg.Record, tree: QuestionTree) -> PlanningDocument:
        data = dict(row)
        data["_id"] = data.pop("id")
        return PlanningDocument(
            **{k: data[k] for k in ("_id", "user_id", "status", "created_at", "updated_at")},
            general_answers=GeneralAnswers(**{k: data[k] for k in _GENERAL_ANSWER_FIELDS}),
            tree=tree,
        )
