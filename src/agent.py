from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from classifier import build_next_memory_state, classify_tickets
from config import Settings
from jira_client import JiraBoardContext, JiraTicket
from llm_usage import aggregate_weekly_llm_usage, format_weekly_usage_block
from message_builder import build_vertical_message, build_weekly_cpo_message
from models import AgentMemoryState, RoadmapPlan, TicketFacts, VerticalPlan
from planner import build_vertical_plan

_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def run_agent(
    settings: Settings,
    tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    board_context: JiraBoardContext | None,
    memory_state: AgentMemoryState,
    skip_roadmap: bool = False,
    force_roadmap: bool = False,
    is_weekly_run: bool = False,
) -> Tuple[Dict[str, VerticalPlan], List[Tuple[str, str, str]], Optional[str], AgentMemoryState, Optional[RoadmapPlan], Dict[str, List[TicketFacts]]]:
    grouped_facts = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        unchanged_stale_days=settings.unchanged_stale_days,
        last_message_sent_at=memory_state.last_message_sent_at,
        last_sent_tickets=memory_state.last_sent_tickets,
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
            last_run_at=memory_state.last_message_sent_at,
        )
        outbound_messages.append((vertical, title, body))

    recurring_patterns = None
    if settings.llm_webhook_url:
        try:
            from recurrence_analyzer import analyze_recurrence, build_next_recurrence_memory
            recurring_patterns, _ = analyze_recurrence(
                active_tickets=tickets,
                finalized_tickets=finalized_tickets,
                webhook_url=settings.llm_webhook_url,
                webhook_secret=settings.llm_webhook_secret,
                recurrence_memory=memory_state.recurrence,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de recurrencia falló: {exc}")

    next_memory = build_next_memory_state(grouped_facts)
    # Preservar secciones existentes para que main.py las actualice
    next_memory.roadmap = memory_state.roadmap
    if recurring_patterns is not None:
        next_memory.recurrence = build_next_recurrence_memory(
            previous=memory_state.recurrence,
            new_patterns=recurring_patterns,
            all_tickets=tickets + finalized_tickets,
        )
    else:
        next_memory.recurrence = memory_state.recurrence

    # Weekly CPO message (only on Friday runs)
    cpo_body = None
    if is_weekly_run:
        today = datetime.now(_ARGENTINA_TZ).date()
        # week_end = el viernes más reciente (hoy si es viernes, sino el último viernes)
        days_since_friday = (today.weekday() - 4) % 7
        week_end = today - timedelta(days=days_since_friday)
        week_start = week_end - timedelta(days=4)  # lunes de esa semana
        week_start_str = week_start.isoformat()
        resolved_this_week = [
            t for t in finalized_tickets
            if t.last_status_change_at[:10] >= week_start_str
        ]
        active_facts = [f for facts in grouped_facts.values() for f in facts]
        cpo_body = build_weekly_cpo_message(
            project_label=project_label,
            active_facts=active_facts,
            resolved_this_week=resolved_this_week,
            week_start=week_start,
            week_end=week_end,
            recurring_patterns=recurring_patterns,
        )

        # LLM usage agregado de la semana (incluye runs diarios + roadmap-only)
        usage = aggregate_weekly_llm_usage(week_start=week_start, week_end=week_end)
        cpo_body += "\n" + format_weekly_usage_block(usage)

    # Roadmap analysis (weekly only, or forced)
    roadmap_plan = None
    if (is_weekly_run or force_roadmap) and not skip_roadmap:
        try:
            roadmap_plan = _run_roadmap_analysis(
                settings=settings,
                tickets=tickets,
                finalized_tickets=finalized_tickets,
                recurring_patterns=recurring_patterns or [],
                memory_state=memory_state,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de roadmap falló: {exc}")

    return plans, outbound_messages, cpo_body, next_memory, roadmap_plan, grouped_facts


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
        last_message_sent_at=memory_state.last_message_sent_at,
    )
    all_facts = [f for facts in grouped.values() for f in facts]
    has_changes = any(f.created_since_last_message or f.status_changed for f in all_facts)

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


def _run_roadmap_analysis(settings, tickets, finalized_tickets, recurring_patterns, memory_state):
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
        finalized_tickets=finalized_tickets,
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
