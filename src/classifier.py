from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Iterable, List
from zoneinfo import ZoneInfo

from jira_client import JiraTicket
from models import AgentMemoryState, TicketFacts, TicketStateSnapshot

_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def resolve_vertical(
    labels: Iterable[str],
    label_prefix: str,
    label_to_vertical: Dict[str, str],
) -> str:
    labels_lower = [label.lower() for label in labels]

    for label in labels_lower:
        if label.startswith(label_prefix):
            vertical = label[len(label_prefix) :].strip()
            if vertical:
                return vertical

    for label in labels_lower:
        mapped = label_to_vertical.get(label)
        if mapped:
            return mapped

    return "sin_vertical"


def classify_tickets(
    tickets: List[JiraTicket],
    memory_state: AgentMemoryState,
    label_prefix: str,
    label_to_vertical: Dict[str, str],
    stale_ticket_days: int,
) -> Dict[str, List[TicketFacts]]:
    grouped: Dict[str, List[TicketFacts]] = defaultdict(list)
    now_local = datetime.now(tz=_ARGENTINA_TZ)
    stale_cutoff = now_local - timedelta(days=stale_ticket_days)

    for ticket in tickets:
        vertical = resolve_vertical(ticket.labels, label_prefix, label_to_vertical)
        previous = memory_state.tickets.get(ticket.key)
        created_dt = _safe_parse_jira_datetime(ticket.created)
        last_status_change_dt = _safe_parse_jira_datetime(ticket.last_status_change_at)

        facts = TicketFacts(
            key=ticket.key,
            vertical=vertical,
            summary=ticket.summary,
            status=ticket.status,
            status_category=ticket.status_category,
            assignee=ticket.assignee,
            reporter=ticket.reporter,
            created=ticket.created,
            updated=ticket.updated,
            last_status_change_at=ticket.last_status_change_at,
            description=ticket.description,
            section=ticket.section,
            criticality=ticket.criticality,
            environment=ticket.environment,
            ticket_type=ticket.ticket_type,
            url=ticket.url,
            labels=ticket.labels,
            created_today=_is_same_local_day(created_dt, now_local),
            status_changed_today=_is_same_local_day(last_status_change_dt, now_local),
            finalized_today=ticket.status_category.lower() == "done" and _is_same_local_day(last_status_change_dt, now_local),
            is_stale=bool(last_status_change_dt and last_status_change_dt.astimezone() <= stale_cutoff),
            changed_since_last_run=_changed_since_last_run(ticket, previous),
            status_changed=bool(previous and previous.status != ticket.status),
            assignee_changed=bool(previous and previous.assignee != ticket.assignee),
        )
        grouped[vertical].append(facts)

    return dict(sorted(grouped.items(), key=lambda item: item[0]))


def build_next_memory_state(grouped_facts: Dict[str, List[TicketFacts]]) -> AgentMemoryState:
    tickets: Dict[str, TicketStateSnapshot] = {}
    for vertical_facts in grouped_facts.values():
        for facts in vertical_facts:
            tickets[facts.key] = TicketStateSnapshot(
                key=facts.key,
                vertical=facts.vertical,
                status=facts.status,
                assignee=facts.assignee,
                updated=facts.updated,
                last_status_change_at=facts.last_status_change_at,
                notified_reasons=[],
            )
    return AgentMemoryState(tickets=tickets)


def _changed_since_last_run(ticket: JiraTicket, previous: TicketStateSnapshot | None) -> bool:
    if previous is None:
        return True
    return (
        previous.updated != ticket.updated
        or previous.status != ticket.status
        or previous.assignee != ticket.assignee
        or previous.last_status_change_at != ticket.last_status_change_at
    )


def _is_same_local_day(value: datetime | None, reference: datetime) -> bool:
    if value is None:
        return False
    return value.astimezone(reference.tzinfo).date() == reference.date()


def _safe_parse_jira_datetime(raw_value: str) -> datetime | None:
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        try:
            return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            return None
