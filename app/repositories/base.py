import uuid
from typing import Generic, Optional, TypeVar

import asyncpg
from pydantic import BaseModel

from app.models.planning import DynamicQuestion, QuestionAnswer, QuestionTree, QuestionTreeNode

T = TypeVar("T", bound=BaseModel)


def new_id() -> str:
    return str(uuid.uuid4())


class BaseRepository(Generic[T]):
    def __init__(self, pool: asyncpg.Pool, model_class: type[T]) -> None:
        self._pool = pool
        self._model = model_class


# ---------------------------------------------------------------------------
# Shared persistence helpers for the question decision tree (QuestionTree).
# Used by both PlanningRepository (planning tree) and ItineraryRepository
# (destination replacement trees).
# ---------------------------------------------------------------------------

async def create_tree(conn: asyncpg.Connection, tree: QuestionTree) -> str:
    tree_id = new_id()
    await conn.execute(
        "INSERT INTO question_trees (id, root_id, current_node_id) VALUES ($1, $2, $3)",
        tree_id, tree.root_id, tree.current_node_id,
    )
    await _insert_tree_nodes(conn, tree_id, tree)
    return tree_id


async def update_tree(conn: asyncpg.Connection, tree_id: str, tree: QuestionTree) -> None:
    await conn.execute(
        "UPDATE question_trees SET root_id = $2, current_node_id = $3 WHERE id = $1",
        tree_id, tree.root_id, tree.current_node_id,
    )
    await conn.execute("DELETE FROM question_nodes WHERE tree_id = $1", tree_id)
    await _insert_tree_nodes(conn, tree_id, tree)


async def delete_tree(conn: asyncpg.Connection, tree_id: str) -> None:
    await conn.execute("DELETE FROM question_trees WHERE id = $1", tree_id)


async def load_tree(conn: asyncpg.Connection, tree_id: str) -> QuestionTree:
    tree_row = await conn.fetchrow("SELECT * FROM question_trees WHERE id = $1", tree_id)
    if not tree_row:
        return QuestionTree()

    node_rows = await conn.fetch(
        "SELECT * FROM question_nodes WHERE tree_id = $1 ORDER BY created_at, node_id",
        tree_id,
    )
    question_rows = await conn.fetch(
        """
        SELECT q.* FROM node_questions q
        JOIN question_nodes n ON n.node_id = q.node_id
        WHERE n.tree_id = $1
        ORDER BY q.position
        """,
        tree_id,
    )
    option_rows = await conn.fetch(
        """
        SELECT o.* FROM question_options o
        JOIN node_questions q ON q.node_id = o.node_id AND q.question_id = o.question_id
        JOIN question_nodes n ON n.node_id = q.node_id
        WHERE n.tree_id = $1
        ORDER BY o.position
        """,
        tree_id,
    )
    answer_rows = await conn.fetch(
        """
        SELECT a.* FROM node_answers a
        JOIN question_nodes n ON n.node_id = a.node_id
        WHERE n.tree_id = $1
        ORDER BY a.position
        """,
        tree_id,
    )
    item_rows = await conn.fetch(
        """
        SELECT i.* FROM answer_items i
        JOIN node_answers a ON a.node_id = i.node_id AND a.question_id = i.question_id
        JOIN question_nodes n ON n.node_id = a.node_id
        WHERE n.tree_id = $1
        ORDER BY i.position
        """,
        tree_id,
    )

    options_by_question: dict[tuple[str, str], list[str]] = {}
    for row in option_rows:
        options_by_question.setdefault((row["node_id"], row["question_id"]), []).append(row["option_text"])

    questions_by_node: dict[str, list[DynamicQuestion]] = {}
    for row in question_rows:
        key = (row["node_id"], row["question_id"])
        questions_by_node.setdefault(row["node_id"], []).append(
            DynamicQuestion(
                question_id=row["question_id"],
                question_text=row["question_text"],
                question_type=row["question_type"],
                options=options_by_question.get(key) or None,
                required=row["required"],
            )
        )

    items_by_answer: dict[tuple[str, str], list[str]] = {}
    for row in item_rows:
        items_by_answer.setdefault((row["node_id"], row["question_id"]), []).append(row["item"])

    answers_by_node: dict[str, list[QuestionAnswer]] = {}
    for row in answer_rows:
        answers_by_node.setdefault(row["node_id"], []).append(
            QuestionAnswer(
                question_id=row["question_id"],
                answer=_decode_answer(row, items_by_answer),
            )
        )

    nodes: dict[str, QuestionTreeNode] = {}
    for row in node_rows:
        node_answers = answers_by_node.get(row["node_id"])
        node = QuestionTreeNode(
            node_id=row["node_id"],
            parent_id=row["parent_id"],
            depth=row["depth"],
            questions=questions_by_node.get(row["node_id"], []),
            answers=node_answers if node_answers else None,
            created_at=row["created_at"],
            answered_at=row["answered_at"],
        )
        nodes[node.node_id] = node
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children_ids.append(node.node_id)

    return QuestionTree(
        nodes=nodes,
        root_id=tree_row["root_id"],
        current_node_id=tree_row["current_node_id"],
    )


async def _insert_tree_nodes(conn: asyncpg.Connection, tree_id: str, tree: QuestionTree) -> None:
    # Insert parents before children (ordered by depth) to satisfy the self-FK.
    for node in sorted(tree.nodes.values(), key=lambda n: n.depth):
        await conn.execute(
            """
            INSERT INTO question_nodes (node_id, tree_id, parent_id, depth, created_at, answered_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            node.node_id, tree_id, node.parent_id, node.depth, node.created_at, node.answered_at,
        )
        for pos, question in enumerate(node.questions):
            await conn.execute(
                """
                INSERT INTO node_questions (node_id, question_id, question_text, question_type, required, position)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                node.node_id, question.question_id, question.question_text,
                question.question_type.value, question.required, pos,
            )
            for opt_pos, option in enumerate(question.options or []):
                await conn.execute(
                    """
                    INSERT INTO question_options (node_id, question_id, option_text, position)
                    VALUES ($1, $2, $3, $4)
                    """,
                    node.node_id, question.question_id, option, opt_pos,
                )
        for ans_pos, answer in enumerate(node.answers or []):
            answer_type, answer_text, answer_number, items = _encode_answer(answer.answer)
            await conn.execute(
                """
                INSERT INTO node_answers (node_id, question_id, answer_type, answer_text, answer_number, position)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                node.node_id, answer.question_id, answer_type, answer_text, answer_number, ans_pos,
            )
            for item_pos, item in enumerate(items):
                await conn.execute(
                    """
                    INSERT INTO answer_items (node_id, question_id, item, position)
                    VALUES ($1, $2, $3, $4)
                    """,
                    node.node_id, answer.question_id, item, item_pos,
                )


def _encode_answer(value) -> tuple[str, Optional[str], Optional[float], list[str]]:
    """Encodes a polymorphic answer value into typed columns."""
    if isinstance(value, bool):
        return "bool", "true" if value else "false", None, []
    if isinstance(value, int):
        return "int", None, float(value), []
    if isinstance(value, float):
        return "float", None, value, []
    if isinstance(value, list):
        return "list", None, None, [str(item) for item in value]
    if isinstance(value, str):
        return "text", value, None, []
    return "text", str(value), None, []


def _decode_answer(row: asyncpg.Record, items_by_answer: dict[tuple[str, str], list[str]]):
    answer_type = row["answer_type"]
    if answer_type == "list":
        return items_by_answer.get((row["node_id"], row["question_id"]), [])
    if answer_type == "int":
        return int(row["answer_number"])
    if answer_type == "float":
        return float(row["answer_number"])
    if answer_type == "bool":
        return row["answer_text"] == "true"
    return row["answer_text"]
