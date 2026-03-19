import json
from dataclasses import dataclass
from typing import List

import anthropic

from jira_client import JiraTicket


@dataclass
class RecurringPattern:
    label: str
    ticket_keys: List[str]
    count: int
    recommendation: str


def analyze_recurrence(
    active_tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    api_key: str,
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

    prompt = f"""Tenés una lista de tickets de soporte de producción (activos y finalizados).
Tu tarea es identificar patrones recurrentes: grupos de tickets que representan el mismo tipo de problema, aunque estén descritos con distintas palabras.

Enfocate en:
- Errores que se repiten en distintos clientes o entornos
- Fallas en el mismo componente o flujo del sistema
- Problemas de integración que aparecen múltiples veces

Tickets:
{json.dumps(ticket_data, ensure_ascii=False, indent=2)}

Respondé ÚNICAMENTE con un JSON válido con este formato exacto (sin texto adicional):
[
  {{
    "label": "Nombre corto del patrón (ej: 'Fallas en envío de correos')",
    "ticket_keys": ["PS-123", "PS-456"],
    "recommendation": "Una línea concreta para el roadmap (ej: 'Priorizar refactor del módulo de notificaciones')"
  }}
]

Solo incluí grupos con 2 o más tickets. Máximo 8 patrones. Omití grupos triviales."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
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
