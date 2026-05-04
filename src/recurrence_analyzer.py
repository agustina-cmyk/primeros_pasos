import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import requests

from jira_client import JiraTicket
from models import RecurrenceMemoryState, RecurringPatternSnapshot


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
    webhook_secret: str = "",
    recurrence_memory: Optional[RecurrenceMemoryState] = None,
) -> Tuple[List[RecurringPatternSnapshot], dict]:
    if recurrence_memory is None:
        recurrence_memory = RecurrenceMemoryState()

    all_tickets = active_tickets + finalized_tickets
    if len(all_tickets) < 2:
        return recurrence_memory.patterns, {}

    already_analyzed = set(recurrence_memory.analyzed_ticket_keys)
    new_tickets = [t for t in all_tickets if t.key not in already_analyzed]

    # Si no hay tickets nuevos, devolver patrones existentes tal cual
    if not new_tickets:
        print("[RECURRENCE] Sin tickets nuevos — usando patrones en memoria.")
        return recurrence_memory.patterns, {}

    # Armar contexto: tickets nuevos completos + resumen de patrones previos
    ticket_data = [
        {
            "key": t.key,
            "status": t.status,
            "summary": t.summary,
            "description": t.description[:300] if t.description else "",
        }
        for t in new_tickets
    ]

    existing_patterns_summary = [
        {"label": p.label, "ticket_keys": p.ticket_keys, "recommendation": p.recommendation}
        for p in recurrence_memory.patterns
    ]

    user_message = (
        f"Tickets nuevos desde el último análisis ({len(new_tickets)} tickets):\n"
        f"{json.dumps(ticket_data, ensure_ascii=False, indent=2)}\n\n"
    )
    if existing_patterns_summary:
        user_message += (
            f"Patrones ya detectados en análisis anteriores (pueden actualizarse si estos tickets los refuerzan):\n"
            f"{json.dumps(existing_patterns_summary, ensure_ascii=False, indent=2)}\n\n"
            f"Si un ticket nuevo pertenece a un patrón existente, incluilo en ese patrón con el mismo label. "
            f"Si encontrás un patrón nuevo, agregalo. Si un patrón existente ya no tiene soporte en tickets activos/recientes, omitilo."
        )
    else:
        user_message += "No hay patrones previos. Identificá los patrones desde cero."

    payload = {"system_prompt": _SYSTEM_PROMPT, "user_message": user_message}
    input_stats = _log_llm_input(payload, new_ticket_count=len(new_tickets), total_ticket_count=len(all_tickets))

    headers = {"X-Webhook-Secret": webhook_secret} if webhook_secret else {}
    response = requests.post(
        webhook_url,
        json=payload,
        headers=headers,
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

    groups = json.loads(raw)
    today_str = datetime.now(timezone.utc).date().isoformat()
    patterns = []
    for g in groups:
        keys = g.get("ticket_keys", [])
        if len(keys) >= 2:
            patterns.append(RecurringPatternSnapshot(
                label=g.get("label", ""),
                ticket_keys=keys,
                count=len(keys),
                recommendation=g.get("recommendation", ""),
                last_seen_at=today_str,
            ))

    patterns.sort(key=lambda p: p.count, reverse=True)
    return patterns, input_stats


def build_next_recurrence_memory(
    previous: RecurrenceMemoryState,
    new_patterns: List[RecurringPatternSnapshot],
    all_tickets: List[JiraTicket],
) -> RecurrenceMemoryState:
    """Construye el nuevo estado de memoria de recurrencia para persistir."""
    return RecurrenceMemoryState(
        patterns=new_patterns,
        analyzed_ticket_keys=[t.key for t in all_tickets],
        last_run_at=datetime.now(timezone.utc).isoformat(),
    )


def _log_llm_input(payload: dict, new_ticket_count: int, total_ticket_count: int) -> dict:
    stats = {}
    try:
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"reports/recurrence_input_{timestamp}.json"
        system_chars = len(payload.get("system_prompt", ""))
        user_chars = len(payload.get("user_message", ""))
        total_chars = system_chars + user_chars
        stats = {
            "system_prompt_chars": system_chars,
            "user_message_chars": user_chars,
            "total_chars": total_chars,
            "estimated_tokens": round(total_chars / 4),
            "new_tickets_sent": new_ticket_count,
            "total_tickets_in_board": total_ticket_count,
            "log_path": path,
        }
        log = {
            "timestamp": timestamp,
            "stats": stats,
            "system_prompt": payload.get("system_prompt", ""),
            "user_message": payload.get("user_message", ""),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        print(
            f"[RECURRENCE] Input LLM guardado en: {path} "
            f"({new_ticket_count}/{total_ticket_count} tickets nuevos, "
            f"{total_chars} chars, ~{round(total_chars / 4)} tokens)"
        )
    except Exception as exc:
        print(f"[WARN] No se pudo guardar el input de recurrencia: {exc}")
    return stats
