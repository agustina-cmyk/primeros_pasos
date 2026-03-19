from typing import Dict, List, Optional, Tuple

from classifier import build_next_memory_state, classify_tickets
from config import Settings
from jira_client import JiraBoardContext, JiraTicket
from jira_client import JiraTicket
from message_builder import build_cpo_message, build_vertical_message
from models import AgentMemoryState, VerticalPlan
from planner import build_vertical_plan


def run_agent(
    settings: Settings,
    tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    board_context: JiraBoardContext | None,
    memory_state: AgentMemoryState,
) -> Tuple[Dict[str, VerticalPlan], List[Tuple[str, str, str]], Optional[str], AgentMemoryState]:
    grouped_facts = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        stale_ticket_days=settings.stale_ticket_days,
    )

    project_label = _project_label(settings.jira_board_id, board_context)
    plans: Dict[str, VerticalPlan] = {}
    outbound_messages: List[Tuple[str, str, str]] = []

    for vertical, facts in grouped_facts.items():
        plan = build_vertical_plan(vertical=vertical, tickets=facts)
        plans[vertical] = plan
        if not plan.actions:
            continue

        title, body = build_vertical_message(
            project_label=project_label,
            plan=plan,
            channel_url=settings.roam_channel_urls.get(vertical, ""),
            max_items=settings.max_items_per_vertical,
            last_run_at=memory_state.last_run_at,
        )
        outbound_messages.append((vertical, title, body))

    recurring_patterns = None
    if settings.llm_webhook_url:
        try:
            from recurrence_analyzer import analyze_recurrence
            recurring_patterns = analyze_recurrence(
                active_tickets=tickets,
                finalized_tickets=finalized_tickets,
                webhook_url=settings.llm_webhook_url,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de recurrencia falló: {exc}")

    cpo_body = build_cpo_message(
        project_label=project_label,
        grouped_facts=grouped_facts,
        recurring_patterns=recurring_patterns,
    )
    next_memory = build_next_memory_state(grouped_facts)
    return plans, outbound_messages, cpo_body, next_memory


def _project_label(board_id: str, board_context: JiraBoardContext | None) -> str:
    if board_context is None:
        return f"Board {board_id}"
    return board_context.project_name or board_context.project_key or board_context.board_name
