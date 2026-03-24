from typing import List

from models import AgentAction, TicketFacts, VerticalPlan


def build_vertical_plan(vertical: str, tickets: List[TicketFacts]) -> VerticalPlan:
    actions: List[AgentAction] = []

    # Excluir tickets done que no finalizaron hoy
    active = [t for t in tickets if t.status_category.lower() != "done" or t.finalized_today]

    # Bucket 1: cambios (status_changed, created_today, finalized_today)
    changes = [
        t for t in active
        if t.status_changed or t.created_today or t.finalized_today
    ]
    changes_keys = {t.key for t in changes}

    # Buckets de sin movimiento (solo tickets que no están en changes)
    unchanged = [t for t in active if t.key not in changes_keys]
    recent = [t for t in unchanged if not t.is_stale]
    stale = [t for t in unchanged if t.is_stale]

    if changes:
        actions.append(AgentAction(
            action_type="notify_changes",
            vertical=vertical,
            reason="Tickets con cambios desde la última corrida.",
            tickets=_sort_changes(changes),
        ))

    if recent:
        actions.append(AgentAction(
            action_type="notify_unchanged_recent",
            vertical=vertical,
            reason="Tickets activos sin cambio de estado en menos de 5 días.",
            tickets=_sort_recent(recent),
        ))

    if stale:
        actions.append(AgentAction(
            action_type="notify_unchanged_stale",
            vertical=vertical,
            reason="Tickets activos sin cambio de estado en 5 días o más.",
            tickets=_sort_stale(stale),
        ))

    return VerticalPlan(vertical=vertical, actions=actions)


def _sort_changes(tickets: List[TicketFacts]) -> List[TicketFacts]:
    return sorted(tickets, key=lambda t: t.updated, reverse=True)


def _sort_recent(tickets: List[TicketFacts]) -> List[TicketFacts]:
    return sorted(tickets, key=lambda t: t.days_without_status_change)


def _sort_stale(tickets: List[TicketFacts]) -> List[TicketFacts]:
    return sorted(
        tickets,
        key=lambda t: (
            0 if (t.criticality or "").lower() == "highest" else 1,
            -t.days_without_status_change,
        ),
    )
