import uuid
from datetime import datetime
from app.models.planning import (
    DynamicQuestion,
    GeneralAnswers,
    QuestionAnswer,
    QuestionTree,
    QuestionTreeNode,
)


class DecisionTreeManager:
    """
    Manages the lifecycle of the question decision tree for a planning session.
    Encapsulates all tree mutation logic so services stay clean.
    """

    @staticmethod
    def create_root_node(questions: list[DynamicQuestion]) -> tuple[QuestionTree, QuestionTreeNode]:
        node = QuestionTreeNode(
            node_id=str(uuid.uuid4()),
            parent_id=None,
            depth=0,
            questions=questions,
        )
        tree = QuestionTree(
            nodes={node.node_id: node},
            root_id=node.node_id,
            current_node_id=node.node_id,
        )
        return tree, node

    @staticmethod
    def answer_node(
        tree: QuestionTree,
        node_id: str,
        answers: list[QuestionAnswer],
    ) -> QuestionTreeNode:
        node = tree.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found in tree")
        if node.is_answered():
            raise ValueError(f"Node {node_id} already answered")
        node.answers = answers
        node.answered_at = datetime.utcnow()
        return node

    @staticmethod
    def append_child_node(
        tree: QuestionTree,
        parent_id: str,
        questions: list[DynamicQuestion],
    ) -> QuestionTreeNode:
        parent = tree.nodes.get(parent_id)
        if not parent:
            raise ValueError(f"Parent node {parent_id} not found")

        child = QuestionTreeNode(
            node_id=str(uuid.uuid4()),
            parent_id=parent_id,
            depth=parent.depth + 1,
            questions=questions,
        )
        tree.add_node(child)
        tree.current_node_id = child.node_id
        return child

    @staticmethod
    def build_context_summary(
        general_answers: GeneralAnswers,
        tree: QuestionTree,
        current_node_id: str,
    ) -> str:
        """Builds a human-readable summary of all answers up to the current node."""
        lines = [
            "=== RESPUESTAS GENERALES ===",
            f"Destino: {general_answers.destination_country}"
            + (f", {general_answers.destination_city}" if general_answers.destination_city else ""),
            f"Fechas: {general_answers.arrival_date} → {general_answers.departure_date}",
            f"Días totales: {general_answers.total_days}",
            f"Viajeros: {general_answers.number_of_travelers}",
            f"Presupuesto: {general_answers.budget_range.value}",
            f"Propósito: {general_answers.travel_purpose.value}",
            f"Viajan niños: {'Sí' if general_answers.has_children else 'No'}",
        ]
        if general_answers.special_requirements:
            lines.append(f"Requerimientos especiales: {general_answers.special_requirements}")

        path = tree.get_path_to_node(current_node_id)
        if path:
            lines.append("\n=== RESPUESTAS DINÁMICAS ===")
            for node in path:
                if not node.answers:
                    continue
                answer_map = {a.question_id: a.answer for a in node.answers}
                for q in node.questions:
                    answer = answer_map.get(q.question_id, "(sin respuesta)")
                    lines.append(f"- {q.question_text}: {answer}")

        return "\n".join(lines)

    @staticmethod
    def create_replacement_root(questions: list[DynamicQuestion]) -> tuple[QuestionTree, QuestionTreeNode]:
        return DecisionTreeManager.create_root_node(questions)
