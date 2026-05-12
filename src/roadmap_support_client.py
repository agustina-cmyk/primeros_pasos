"""Cliente HTTP para sincronizar tickets de soporte a la roadmap-app.

Endpoint: POST {app_url}/api/support-tickets/sync
Auth: Bearer token (Supabase access token, mismo patrón que roadmap_client.py)
"""

from dataclasses import dataclass
from typing import List, Dict, Any

import requests

from models import TicketFacts


@dataclass(frozen=True)
class SyncResult:
    synced: int
    errors: List[Dict[str, str]]  # cada item: { "key": str, "message": str }


def _ticket_to_payload(facts: TicketFacts) -> Dict[str, Any]:
    """Convierte un TicketFacts al shape esperado por el endpoint."""
    resolved_at = facts.last_status_change_at if facts.status_category == "Done" else None
    return {
        "key":         facts.key,
        "createdAt":   facts.created,
        "resolvedAt":  resolved_at,
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
