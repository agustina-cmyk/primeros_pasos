from typing import List

from models import AgentAction, TicketFacts, VerticalPlan


def build_vertical_plan(vertical: str, tickets: List[TicketFacts]) -> VerticalPlan:
    actions: List[AgentAction] = []

    created_today = [ticket for ticket in tickets if ticket.created_today]
    finished_today = [ticket for ticket in tickets if ticket.finalized_today]
    stale = [ticket for ticket in tickets if ticket.is_stale]

    if created_today:
        actions.append(
            AgentAction(
                action_type="notify_created_today",
                vertical=vertical,
                reason="Tickets creados hoy.",
                tickets=_sort_tickets(created_today),
            )
        )

    if finished_today:
        actions.append(
            AgentAction(
                action_type="notify_finished_today",
                vertical=vertical,
                reason="Tickets que cambiaron de estado hoy y quedaron finalizados.",
                tickets=_sort_tickets(finished_today),
            )
        )

    status_changed = [
        t for t in tickets
        if t.status_changed and not t.finalized_today
    ]
    if status_changed:
        actions.append(
            AgentAction(
                action_type="notify_status_changed",
                vertical=vertical,
                reason="Tickets que cambiaron de estado desde la última corrida.",
                tickets=_sort_tickets(status_changed),
            )
        )

    if stale:
        actions.append(
            AgentAction(
                action_type="notify_stale_tickets",
                vertical=vertical,
                reason="Tickets estancados sin cambio de estado en los ultimos 15 dias.",
                tickets=_sort_tickets(stale),
            )
        )

    return VerticalPlan(vertical=vertical, actions=actions)


def _sort_tickets(tickets: List[TicketFacts]) -> List[TicketFacts]:
    return sorted(tickets, key=lambda ticket: (ticket.updated, ticket.key), reverse=True)
