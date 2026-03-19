import json
from dataclasses import dataclass
from typing import List

import requests

from jira_client import JiraTicket


@dataclass
class RecurringPattern:
    label: str
    ticket_keys: List[str]
    count: int
    recommendation: str


_SYSTEM_PROMPT = """Sos un analista de soporte técnico. Tu tarea es identificar patrones recurrentes en tickets de producción: grupos de tickets que representan el mismo tipo de problema, aunque estén descritos con distintas palabras.

Enfocate en:
- Errores que se repiten en distintos clientes o entornos
- Fallas en el mismo componente o flujo del sistema
- Problemas de integración que aparecen múltiples veces

Respondé ÚNICAMENTE con un JSON válido con este formato exacto (sin texto adicional):
[
  {
    "label": "Nombre corto del patrón (ej: 'Fallas en envío de correos')",
    "ticket_keys": ["PS-123", "PS-456"],
    "recommendation": "Una línea concreta para el roadmap (ej: 'Priorizar refactor del módulo de notificaciones')"
  }
]

Solo incluí grupos con 2 o más tickets. Máximo 8 patrones. Omití grupos triviales."""


def analyze_recurrence(
    active_tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    webhook_url: str,
) -> List[RecurringPattern]:
    all_tickets = active_tickets + finalized_tickets
    if len(all_tickets) < 2:
        return []

    ticket_data = [
        {
            "key": t.key,
            "status": t.status,
            "summary": t.summary,
            "description": t.description[:300] if t.description else "",
        }
        for t in all_tickets
    ]

    user_message = f"""Tenés una lista de tickets de soporte de producción (activos y finalizados). Identificá los patrones recurrentes.

Tickets:
{json.dumps(ticket_data, ensure_ascii=False, indent=2)}"""

    response = requests.post(
        webhook_url,
        json={"system_prompt": _SYSTEM_PROMPT, "user_message": user_message},
        timeout=120,
    )
    response.raise_for_status()

    body = response.json()
    raw = (body.get("response") if isinstance(body, dict) else response.text).strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    groups = json.loads(raw)
    patterns = []
    for g in groups:
        keys = g.get("ticket_keys", [])
        if len(keys) >= 2:
            patterns.append(RecurringPattern(
                label=g.get("label", ""),
                ticket_keys=keys,
                count=len(keys),
                recommendation=g.get("recommendation", ""),
            ))

    patterns.sort(key=lambda p: p.count, reverse=True)
    return patterns
