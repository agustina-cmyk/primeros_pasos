from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional
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
    unchanged_stale_days: int,
    last_message_sent_at: Optional[str] = None,
) -> Dict[str, List[TicketFacts]]:
    grouped: Dict[str, List[TicketFacts]] = defaultdict(list)
    now_local = datetime.now(tz=_ARGENTINA_TZ)
    last_message_dt = _safe_parse_iso(last_message_sent_at)

    for ticket in tickets:
        vertical = resolve_vertical(ticket.labels, label_prefix, label_to_vertical)
        previous = memory_state.tickets.get(ticket.key)
        created_dt = _safe_parse_jira_datetime(ticket.created)
        last_status_change_dt = _safe_parse_jira_datetime(ticket.last_status_change_at)

        days = _compute_days_without_status_change(
            last_status_change_at=ticket.last_status_change_at,
            created=ticket.created,
            now=now_local,
        )

        created_today = _is_same_local_day(created_dt, now_local)
        finalized_today = ticket.status_category.lower() == "done" and _is_same_local_day(last_status_change_dt, now_local)
        created_since_last_message = (
            _is_after(created_dt, last_message_dt) if last_message_dt else created_today
        )
        finalized_since_last_message = ticket.status_category.lower() == "done" and (
            _is_after(last_status_change_dt, last_message_dt) if last_message_dt else finalized_today
        )

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
            created_today=created_today,
            finalized_today=finalized_today,
            created_since_last_message=created_since_last_message,
            finalized_since_last_message=finalized_since_last_message,
            is_stale=days >= unchanged_stale_days,
            days_without_status_change=days,
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


def _compute_days_without_status_change(
    last_status_change_at: str,
    created: str,
    now: datetime,
) -> int:
    anchor = _safe_parse_jira_datetime(last_status_change_at)
    if anchor is None:
        anchor = _safe_parse_jira_datetime(created)
    if anchor is None:
        return 999
    return (now.date() - anchor.astimezone(now.tzinfo).date()).days


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


def _safe_parse_iso(raw_value: Optional[str]) -> datetime | None:
    if not raw_value:
        return None
    try:
        dt = datetime.fromisoformat(raw_value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _is_after(dt: datetime | None, reference: datetime | None) -> bool:
    if dt is None or reference is None:
        return False
    return dt > reference


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
