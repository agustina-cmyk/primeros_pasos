import json
from typing import List

import requests

from models import (
    NewIdeaData,
    RoadmapAction,
    RoadmapIdea,
    RoadmapMemoryState,
    RoadmapPlan,
)

_MAX_ACTIONS = 5
_ACTION_PRIORITY = ["reply_comment", "vote", "comment", "create_idea"]

_SYSTEM_PROMPT = """Sos un representante del equipo de operaciones dentro del roadmap de producto de Vaas.
Tu tarea es analizar los problemas recurrentes del tablero de Production Support y determinar acciones concretas en el roadmap.

Reglas:
- Solo proponés acciones cuando tenés evidencia clara de tickets reales.
- Votás positivamente ideas que resuelven problemas documentados en Jira.
- Votás negativamente solo si una idea contradice activamente un problema conocido.
- Creás ideas nuevas (create_idea) solo cuando no existe ninguna idea relacionada.
- Para reply_comment: respondés preguntas en ideas que vos creaste, con contexto de los tickets originales.
- Máximo 5 acciones en total.
- SIEMPRE incluís comment_body cuando votás (vote), explicando qué tickets de Jira justifican el voto. Ejemplo: "Votamos positivo porque PS-1234 y PS-1256 muestran que este problema bloquea X operaciones por semana."

Respondé ÚNICAMENTE con un JSON válido (sin texto adicional):
[
  {
    "action": "vote" | "comment" | "create_idea" | "reply_comment",
    "idea_id": "string o null",
    "comment_id": "string o null (solo para reply_comment)",
    "vote_type": "like" | "dislike" | null,
    "comment_body": "string o null",
    "new_idea": {"title": "...", "description": "...", "category": "..."} | null
  }
]

Si no hay acciones necesarias, retorná: []"""


def analyze_roadmap(
    active_tickets,
    recurring_patterns,
    ideas: List[RoadmapIdea],
    roadmap_memory: RoadmapMemoryState,
    webhook_url: str,
) -> RoadmapPlan:
    ticket_summaries = []
    for t in active_tickets:
        summary = {"key": getattr(t, "key", ""), "summary": getattr(t, "summary", ""),
                   "status": getattr(t, "status", "")}
        desc = getattr(t, "description", "") or ""
        summary["description"] = desc[:200]
        ticket_summaries.append(summary)

    pattern_summaries = []
    for p in recurring_patterns:
        pattern_summaries.append({
            "label": getattr(p, "label", ""),
            "ticket_keys": getattr(p, "ticket_keys", []),
            "recommendation": getattr(p, "recommendation", ""),
        })

    idea_summaries = [
        {"id": i.id, "title": i.title, "description": i.description[:200],
         "category": i.category, "upvotes": i.upvotes}
        for i in ideas
    ]

    user_message = (
        f"Tickets activos en Production Support:\n{json.dumps(ticket_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Patrones recurrentes detectados:\n{json.dumps(pattern_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Ideas actuales en el roadmap:\n{json.dumps(idea_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Acciones ya realizadas por el agente (no repetir):\n"
        f"- Votadas: {list(roadmap_memory.voted_idea_ids.keys())}\n"
        f"- Comentadas: {roadmap_memory.commented_idea_ids}\n"
        f"- Ideas creadas: {roadmap_memory.created_idea_ids}"
    )

    response = requests.post(
        webhook_url,
        json={"system_prompt": _SYSTEM_PROMPT, "user_message": user_message},
        timeout=120,
    )
    response.raise_for_status()

    body = response.json()
    raw = (body.get("response") if isinstance(body, dict) else response.text).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"roadmap_analyzer: JSON inválido en respuesta del webhook: {exc}") from exc

    if not items:
        return RoadmapPlan(actions=[], skip_reason="Claude no detectó acciones necesarias")

    actions = []
    for item in items:
        new_idea_data = None
        if item.get("new_idea"):
            ni = item["new_idea"]
            new_idea_data = NewIdeaData(
                title=ni.get("title", ""),
                description=ni.get("description", ""),
                category=ni.get("category", ""),
            )
        actions.append(RoadmapAction(
            action=item.get("action", ""),
            idea_id=item.get("idea_id"),
            comment_id=item.get("comment_id"),
            vote_type=item.get("vote_type"),
            comment_body=item.get("comment_body"),
            new_idea=new_idea_data,
        ))

    if len(actions) > _MAX_ACTIONS:
        actions = _apply_cap(actions)

    return RoadmapPlan(actions=actions, skip_reason=None)


def _apply_cap(actions: List[RoadmapAction]) -> List[RoadmapAction]:
    """Mantiene máximo _MAX_ACTIONS acciones, preservando por prioridad."""
    ordered = sorted(actions, key=lambda a: _ACTION_PRIORITY.index(a.action)
                     if a.action in _ACTION_PRIORITY else len(_ACTION_PRIORITY))
    return ordered[:_MAX_ACTIONS]
