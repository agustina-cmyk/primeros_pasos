from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from classifier import build_next_memory_state, classify_tickets
from config import Settings
from jira_client import JiraBoardContext, JiraTicket
from message_builder import build_cpo_message, build_vertical_message
from models import AgentMemoryState, RoadmapPlan, VerticalPlan, WeeklyTicketSnapshot
from planner import build_vertical_plan


def run_agent(
    settings: Settings,
    tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    board_context: JiraBoardContext | None,
    memory_state: AgentMemoryState,
    skip_roadmap: bool = False,
    force_roadmap: bool = False,
) -> Tuple[Dict[str, VerticalPlan], List[Tuple[str, str, str]], Optional[str], AgentMemoryState, Optional[RoadmapPlan]]:
    grouped_facts = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        unchanged_stale_days=settings.unchanged_stale_days,
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
            board_url=settings.jira_board_url,
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
                webhook_secret=settings.llm_webhook_secret,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de recurrencia falló: {exc}")

    cpo_body = build_cpo_message(
        project_label=project_label,
        grouped_facts=grouped_facts,
        recurring_patterns=recurring_patterns,
    )

    # Análisis de roadmap (opcional)
    roadmap_plan = None
    if not skip_roadmap and (force_roadmap or _should_run_roadmap(settings, tickets, memory_state)):
        try:
            roadmap_plan = _run_roadmap_analysis(
                settings=settings,
                tickets=tickets,
                recurring_patterns=recurring_patterns or [],
                memory_state=memory_state,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de roadmap falló: {exc}")

    next_memory = build_next_memory_state(grouped_facts)
    # Preservar la sección roadmap existente para que main.py la actualice
    next_memory.roadmap = memory_state.roadmap

    return plans, outbound_messages, cpo_body, next_memory, roadmap_plan


def _should_run_roadmap(settings: Settings, tickets: List[JiraTicket], memory_state: AgentMemoryState) -> bool:
    """Activa el módulo de roadmap si hay cambios relevantes."""
    if not settings.roadmap_app_url or not settings.ps_agent_email:
        return False

    # Verificar si hay tickets nuevos o con cambio de estado
    grouped = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        unchanged_stale_days=settings.unchanged_stale_days,
    )
    all_facts = [f for facts in grouped.values() for f in facts]
    has_changes = any(f.created_today or f.status_changed for f in all_facts)

    # Verificar si hay ideas votadas sin comentar aún
    voted_without_comment = [
        idea_id for idea_id in memory_state.roadmap.voted_idea_ids
        if idea_id not in memory_state.roadmap.commented_idea_ids
    ]
    if voted_without_comment:
        return True

    # Verificar si hay comentarios sin responder en ideas creadas o votadas por el agente
    has_pending_comments = False
    idea_ids_to_check = list(set(
        memory_state.roadmap.created_idea_ids
        + list(memory_state.roadmap.voted_idea_ids.keys())
    ))
    if idea_ids_to_check:
        try:
            import roadmap_client
            token = roadmap_client.login(
                supabase_url=settings.roadmap_supabase_url,
                anon_key=settings.roadmap_supabase_anon_key,
                email=settings.ps_agent_email,
                password=settings.ps_agent_password,
            )
            for idea_id in idea_ids_to_check:
                comments = roadmap_client.get_comments(settings.roadmap_app_url, token, idea_id)
                for c in comments:
                    if (c.author_email != settings.ps_agent_email
                            and c.id not in memory_state.roadmap.replied_comment_ids):
                        has_pending_comments = True
                        break
                if has_pending_comments:
                    break
        except Exception as exc:
            print(f"[WARN] No se pudieron verificar comentarios pendientes: {exc}")

    return has_changes or has_pending_comments


def _run_roadmap_analysis(settings, tickets, recurring_patterns, memory_state):
    import roadmap_client
    from roadmap_analyzer import analyze_roadmap

    token = roadmap_client.login(
        supabase_url=settings.roadmap_supabase_url,
        anon_key=settings.roadmap_supabase_anon_key,
        email=settings.ps_agent_email,
        password=settings.ps_agent_password,
    )
    ideas = roadmap_client.get_ideas(settings.roadmap_app_url, token)
    return analyze_roadmap(
        active_tickets=tickets,
        recurring_patterns=recurring_patterns,
        ideas=ideas,
        roadmap_memory=memory_state.roadmap,
        webhook_url=settings.llm_webhook_url,
        webhook_secret=settings.llm_webhook_secret,
    )


def _project_label(board_id: str, board_context: JiraBoardContext | None) -> str:
    if board_context is None:
        return f"Board {board_id}"
    return board_context.project_name or board_context.project_key or board_context.board_name


def _build_weekly_snapshot(
    grouped_facts: Dict[str, List],
) -> Dict[str, WeeklyTicketSnapshot]:
    result = {}
    for facts in grouped_facts.values():
        for f in facts:
            result[f.key] = WeeklyTicketSnapshot(
                status=f.status,
                status_category=f.status_category,
                days_without_status_change=f.days_without_status_change,
                is_stale=f.is_stale,
                criticality=f.criticality,
                vertical=f.vertical,
                reporter=f.reporter,
                created=f.created,
                finalized_today=f.finalized_today,
            )
    return result


def _build_next_weekly_buffer(
    memory_state: AgentMemoryState,
    today_str: str,
    grouped_facts: Dict[str, List],
) -> Dict[str, Dict[str, WeeklyTicketSnapshot]]:
    existing = dict(memory_state.weekly_buffer)

    # Stale check: if earliest buffer date is from a different ISO week/year, reset
    if existing:
        earliest = date.fromisoformat(min(existing.keys()))
        today = date.fromisoformat(today_str)
        e_cal = earliest.isocalendar()
        t_cal = today.isocalendar()
        if e_cal.week != t_cal.week or e_cal.year != t_cal.year:
            existing = {}

    today_snapshot = _build_weekly_snapshot(grouped_facts)
    return {**existing, today_str: today_snapshot}
