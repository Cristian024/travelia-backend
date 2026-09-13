from app.models.planning import GeneralAnswers
from app.models.itinerary import Destination

SYSTEM_TRAVEL_PLANNER = """\
Eres Travelia, un asistente experto en planificación de viajes personalizados. \
Ayudas a los usuarios a planificar itinerarios detallados y emocionantes basándote \
en sus preferencias, presupuesto y necesidades específicas. \
Siempre respondes en español y en formato JSON válido cuando se te solicita.\
"""


def build_dynamic_questions_prompt(context_summary: str, depth: int) -> str:
    max_questions = 5 if depth < 2 else 4
    return f"""\
{context_summary}

Con base en toda la información anterior, genera {max_questions} preguntas dinámicas \
y personalizadas para refinar aún más el plan de viaje del usuario. \
Las preguntas deben profundizar en aspectos que aún no han sido cubiertos y que \
son relevantes dado el destino, propósito y preferencias ya indicados.

Responde ÚNICAMENTE con un JSON con esta estructura exacta (sin texto adicional):
{{
  "questions": [
    {{
      "question_id": "q_<uuid_corto>",
      "question_text": "Texto de la pregunta en español",
      "question_type": "text|single_choice|multiple_choice|scale|number",
      "options": ["opción1", "opción2"] // solo para single_choice o multiple_choice, null para otros
    }}
  ]
}}

Reglas:
- question_type debe ser uno de: text, single_choice, multiple_choice, scale, number
- Para "scale": omite options, el usuario responderá del 1 al 5
- Para "text": omite options
- Para "number": omite options
- Cada question_id debe ser único (usa uuid corto de 8 chars)
- Las preguntas deben ser concretas, accionables y útiles para el planificador
- No repitas preguntas que ya han sido respondidas\
"""


def build_generate_itinerary_prompt(context_summary: str, general: GeneralAnswers) -> str:
    return f"""\
{context_summary}

Con base en todos los criterios y preferencias recopilados, crea un itinerario de viaje \
detallado y personalizado para {general.total_days} días ({general.arrival_date} → {general.departure_date}) \
a {general.destination_country}{f', {general.destination_city}' if general.destination_city else ''}.

El itinerario debe distribuir los días entre los mejores destinos/lugares que encajen \
perfectamente con las preferencias del usuario (propósito: {general.travel_purpose.value}, \
presupuesto: {general.budget_range.value}, viajeros: {general.number_of_travelers}).

Responde ÚNICAMENTE con un JSON con esta estructura exacta (sin texto adicional):
{{
  "title": "Título atractivo del itinerario",
  "summary": "Resumen de 2-3 oraciones del itinerario",
  "destinations": [
    {{
      "order": 1,
      "name": "Nombre del lugar/destino",
      "country": "País",
      "city": "Ciudad o región",
      "days_allocated": 3,
      "description": "Descripción del destino y por qué es ideal para este viajero",
      "highlights": ["Atracción 1", "Atracción 2", "Atracción 3"],
      "accommodation_suggestions": ["Hotel o tipo de alojamiento 1", "Opción 2"],
      "transportation": "Cómo llegar y moverse en este destino",
      "estimated_cost": "Estimado en USD por persona (ej: $300-$500)",
      "activities": [
        {{
          "name": "Nombre de la actividad",
          "description": "Breve descripción",
          "duration_hours": 2.5,
          "category": "cultural|aventura|gastronomía|naturaleza|entretenimiento|descanso",
          "estimated_cost": "$20-$40 por persona"
        }}
      ]
    }}
  ]
}}

Reglas:
- La suma de days_allocated de todos los destinos debe ser exactamente {general.total_days}
- Incluye entre 2 y 5 destinos según la duración del viaje
- Incluye 2-4 actividades por destino
- Asegúrate de que todo sea relevante para el propósito y presupuesto del viajero
- Si viajan niños, incluye actividades familiares apropiadas\
"""


def build_replacement_questions_prompt(
    destination: Destination,
    context_summary: str,
    replacement_context: str,
    depth: int,
) -> str:
    max_questions = 4 if depth < 2 else 3
    return f"""\
{context_summary}

=== DESTINO A REEMPLAZAR ===
El usuario NO está satisfecho con el destino "{destination.name}" ({destination.city}, {destination.country}).
Tiene {destination.days_allocated} días asignados para este destino.

{f"=== CONTEXTO DE REEMPLAZO PREVIO ==={chr(10)}{replacement_context}" if replacement_context else ""}

Genera {max_questions} preguntas específicas para entender mejor qué tipo de destino \
alternativo busca el usuario como reemplazo. Enfócate en qué no le gustó del destino \
anterior y qué características debe tener el nuevo destino.

Responde ÚNICAMENTE con un JSON con esta estructura exacta (sin texto adicional):
{{
  "questions": [
    {{
      "question_id": "rq_<uuid_corto>",
      "question_text": "Texto de la pregunta en español",
      "question_type": "text|single_choice|multiple_choice|scale|number",
      "options": ["opción1", "opción2"] // solo para single_choice o multiple_choice, null para otros
    }}
  ]
}}\
"""


def build_replacement_destination_prompt(
    destination: Destination,
    context_summary: str,
    replacement_answers_summary: str,
) -> str:
    return f"""\
{context_summary}

=== DESTINO A REEMPLAZAR ===
Destino actual: "{destination.name}" ({destination.city}, {destination.country})
Días asignados: {destination.days_allocated}

=== PREFERENCIAS PARA EL REEMPLAZO ===
{replacement_answers_summary}

Sugiere UN nuevo destino alternativo que sea significativamente diferente al actual \
pero que encaje perfectamente con las preferencias del usuario.

Responde ÚNICAMENTE con un JSON con esta estructura exacta (sin texto adicional):
{{
  "name": "Nombre del nuevo destino",
  "country": "País",
  "city": "Ciudad o región",
  "description": "Por qué este destino es mejor para el usuario según sus preferencias",
  "highlights": ["Atracción 1", "Atracción 2", "Atracción 3"],
  "accommodation_suggestions": ["Opción 1", "Opción 2"],
  "transportation": "Cómo llegar y moverse",
  "estimated_cost": "Estimado en USD por persona",
  "activities": [
    {{
      "name": "Actividad",
      "description": "Descripción",
      "duration_hours": 2.0,
      "category": "cultural|aventura|gastronomía|naturaleza|entretenimiento|descanso",
      "estimated_cost": "$X-$Y por persona"
    }}
  ]
}}\
"""
