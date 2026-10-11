import json
import uuid
from typing import Any

from app.llm.interfaces import LLMProvider
from app.llm.prompts import (
    SYSTEM_TRAVEL_PLANNER,
    build_dynamic_questions_prompt,
    build_generate_itinerary_prompt,
    build_packing_list_prompt,
    build_replacement_destination_prompt,
    build_replacement_questions_prompt,
)
from app.models.itinerary import Activity, Destination, DestinationReplacement, ItineraryDocument
from app.models.packing import PackingItem, PackingList
from app.models.planning import DynamicQuestion, GeneralAnswers, QuestionType


class LLMClient:
    """
    Orquesta las llamadas al LLM para el dominio de Travelia.
    Depende de LLMProvider (interfaz), no de ningún SDK concreto.
    El parseo de JSON y la construcción de prompts viven aquí;
    el proveedor solo sabe completar texto.
    """

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    def _call(self, prompt: str) -> str:
        return self._provider.complete(system=SYSTEM_TRAVEL_PLANNER, user=prompt)

    def _parse_json(self, raw: str) -> Any:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    def _parse_question(self, q: dict) -> DynamicQuestion:
        try:
            q_type = QuestionType(q.get("question_type", "text"))
        except ValueError:
            q_type = QuestionType.text
        return DynamicQuestion(
            question_id=q.get("question_id", f"q_{uuid.uuid4().hex[:8]}"),
            question_text=q["question_text"],
            question_type=q_type,
            options=q.get("options") or None,
        )

    def generate_dynamic_questions(
        self,
        context_summary: str,
        depth: int,
        max_questions: int | None = None,
        is_premium: bool = False,
    ) -> list[DynamicQuestion]:
        prompt = build_dynamic_questions_prompt(
            context_summary, depth, max_questions=max_questions, is_premium=is_premium
        )
        raw = self._call(prompt)
        data = self._parse_json(raw)
        return [self._parse_question(q) for q in data["questions"]]

    def generate_itinerary_data(
        self,
        context_summary: str,
        general: GeneralAnswers,
        max_destinations: int = 5,
        is_premium: bool = False,
    ) -> dict:
        prompt = build_generate_itinerary_prompt(
            context_summary, general, max_destinations=max_destinations, is_premium=is_premium
        )
        raw = self._call(prompt)
        return self._parse_json(raw)

    def generate_packing_list(
        self,
        itinerary: ItineraryDocument,
        weather_summary: str = "",
        is_premium: bool = False,
    ) -> PackingList:
        prompt = build_packing_list_prompt(itinerary, weather_summary, is_premium)
        raw = self._call(prompt)
        data = self._parse_json(raw)
        destinations = ", ".join(d.name for d in itinerary.destinations) or itinerary.title
        return PackingList(
            itinerary_id=itinerary.id or "",
            destination_summary=destinations,
            weather_summary=weather_summary,
            notes=data.get("notes", ""),
            items=[
                PackingItem(
                    category=item.get("category", "otros"),
                    item=item["item"],
                    quantity=item.get("quantity"),
                    reason=item.get("reason"),
                )
                for item in data.get("items", [])
            ],
        )

    def generate_replacement_questions(
        self,
        destination: Destination,
        context_summary: str,
        replacement_context: str,
        depth: int,
    ) -> list[DynamicQuestion]:
        prompt = build_replacement_questions_prompt(destination, context_summary, replacement_context, depth)
        raw = self._call(prompt)
        data = self._parse_json(raw)
        return [self._parse_question(q) for q in data["questions"]]

    def generate_replacement_destination(
        self,
        destination: Destination,
        context_summary: str,
        replacement_answers_summary: str,
    ) -> dict:
        prompt = build_replacement_destination_prompt(destination, context_summary, replacement_answers_summary)
        raw = self._call(prompt)
        return self._parse_json(raw)

    def build_replacement_context(self, replacement: DestinationReplacement) -> str:
        if not replacement.tree.nodes:
            return ""
        lines: list[str] = []
        for node in replacement.tree.nodes.values():
            if not node.answers:
                continue
            answer_map = {a.question_id: a.answer for a in node.answers}
            for q in node.questions:
                lines.append(f"- {q.question_text}: {answer_map.get(q.question_id, '(sin respuesta)')}")
        return "\n".join(lines)


# --- Helpers para construir modelos de dominio desde respuestas del LLM ---

def _build_activity(raw: dict) -> Activity:
    return Activity(
        activity_id=str(uuid.uuid4()),
        name=raw["name"],
        description=raw.get("description", ""),
        duration_hours=float(raw.get("duration_hours", 1.0)),
        category=raw.get("category", "general"),
        estimated_cost=raw.get("estimated_cost"),
    )


def build_destinations_from_llm(destinations_raw: list[dict]) -> list[Destination]:
    result: list[Destination] = []
    for i, d in enumerate(destinations_raw):
        activities = [_build_activity(a) for a in d.get("activities", [])]
        result.append(Destination(
            destination_id=str(uuid.uuid4()),
            order=d.get("order", i + 1),
            name=d["name"],
            country=d["country"],
            city=d["city"],
            days_allocated=int(d["days_allocated"]),
            description=d.get("description", ""),
            highlights=d.get("highlights", []),
            accommodation_suggestions=d.get("accommodation_suggestions", []),
            transportation=d.get("transportation", ""),
            estimated_cost=d.get("estimated_cost"),
            activities=activities,
        ))
    return result


def build_replacement_destination_from_llm(raw: dict, original: Destination) -> Destination:
    activities = [_build_activity(a) for a in raw.get("activities", [])]
    return Destination(
        destination_id=str(uuid.uuid4()),
        order=original.order,
        name=raw["name"],
        country=raw["country"],
        city=raw["city"],
        days_allocated=original.days_allocated,
        description=raw.get("description", ""),
        highlights=raw.get("highlights", []),
        accommodation_suggestions=raw.get("accommodation_suggestions", []),
        transportation=raw.get("transportation", ""),
        estimated_cost=raw.get("estimated_cost"),
        activities=activities,
    )
