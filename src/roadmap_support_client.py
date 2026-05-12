"""Cliente HTTP para sincronizar tickets de soporte a la roadmap-app.

Endpoint: POST {app_url}/api/support-tickets/sync
Auth: Bearer token (Supabase access token, mismo patrón que roadmap_client.py)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests

from models import TicketFacts


@dataclass(frozen=True)
class SyncResult:
    synced: int
    errors: List[Dict[str, str]]  # cada item: { "key": str, "message": str }


def _normalize_iso(s: str) -> Optional[str]:
    """Normaliza un timestamp de Jira (ej. "2026-04-15T10:00:00.000+0000")
    al formato ISO 8601 estricto en UTC que Zod acepta (ej. "2026-04-15T10:00:00Z").

    El endpoint de roadmap-app usa Zod `.datetime()` sin opciones, que solo
    acepta el sufijo `Z`. Convertimos cualquier timezone a UTC.
    Devuelve None si el input está vacío o no parsea.
    """
    if not s:
        return None
    candidate = s.strip()
    if not candidate:
        return None
    # Convertir +HHMM → +HH:MM (fromisoformat lo requiere en Python <3.11)
    if len(candidate) >= 5:
        offset_char = candidate[-5]
        if offset_char in "+-" and candidate[-4:].isdigit():
            candidate = f"{candidate[:-2]}:{candidate[-2:]}"
    # Convertir Z trailing para fromisoformat
    parseable = candidate.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(parseable)
    except ValueError:
        return None
    # Forzar UTC (Zod .datetime() solo acepta sufijo Z, no offsets)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # isoformat devuelve "+00:00" → reemplazamos por "Z"
    iso = dt.isoformat().replace("+00:00", "Z")
    return iso


def _ticket_to_payload(facts: TicketFacts) -> Dict[str, Any]:
    """Convierte un TicketFacts al shape esperado por el endpoint."""
    raw_resolved = facts.last_status_change_at if facts.status_category == "Done" else None
    return {
        "key":         facts.key,
        "createdAt":   _normalize_iso(facts.created),
        "resolvedAt":  _normalize_iso(raw_resolved) if raw_resolved else None,
        "status":      facts.status,
        "vertical":    facts.vertical,
        "criticality": facts.criticality or None,
        "url":         facts.url,
    }


def sync_support_tickets(
    app_url: str,
    token: str,
    facts: List[TicketFacts],
    timeout: int = 30,
) -> SyncResult:
    """Pushea los tickets clasificados al endpoint /api/support-tickets/sync.

    Idempotente: el endpoint hace upsert por key. Backfill automático en la
    primera corrida (cualquier ticket que el agente vea en el board se sincroniza).
    """
    payload = {"tickets": [_ticket_to_payload(f) for f in facts]}
    response = requests.post(
        f"{app_url.rstrip('/')}/api/support-tickets/sync",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return SyncResult(
        synced=int(data.get("synced", 0)),
        errors=list(data.get("errors", [])),
    )
