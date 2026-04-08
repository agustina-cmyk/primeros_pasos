from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from jira_client import JiraTicket
from models import TicketFacts, VerticalPlan


def build_vertical_message(
    project_label: str,
    plan: VerticalPlan,
    board_url: str,
    max_items: int,
    last_run_at: Optional[str] = None,
) -> Tuple[str, str]:
    # Todos los tickets del plan para el título
    all_tickets = [t for action in plan.actions for t in action.tickets]
    new_in = sum(1 for t in all_tickets if t.created_since_last_message)
    wip = sum(1 for t in all_tickets if t.status_category.lower() != "done" and not t.finalized_today)
    new_out = sum(1 for t in all_tickets if t.finalized_today)

    title = f"{project_label} Daily Update | New In: {new_in} | WIP: {wip} | New Out: {new_out}"

    last_run_label = _format_last_run(last_run_at)
    lines: List[str] = []

    # Índices de acciones por tipo
    actions_by_type = {a.action_type: a for a in plan.actions}

    # --- Sección cambios ---
    changes_action = actions_by_type.get("notify_changes")
    changes_tickets = changes_action.tickets if changes_action else []
    lines.append(f"🔄 **Cambios desde {last_run_label}** ({len(changes_tickets)})")
    lines.append("")
    if changes_tickets:
        for t in changes_tickets:
            lines.append(_ticket_line_changes(t))
        finalized = [t for t in changes_tickets if t.finalized_since_last_message]
        reporters = _unique_reporters(finalized)
        if reporters:
            mentions = ", ".join(f"@{r}" for r in reporters)
            lines.append(f"_{mentions}: sus tickets fueron cerrados hoy_ ✅")
    else:
        lines.append(f"_Sin cambios de estado desde {last_run_label}._")
    lines.append("")

    # --- Sección sin movimiento reciente ---
    recent_action = actions_by_type.get("notify_unchanged_recent")
    recent_tickets = recent_action.tickets if recent_action else []
    lines.append(f"📋 **Sin movimiento — menos de 5 días** ({len(recent_tickets)})")
    lines.append("")
    if recent_tickets:
        for t in recent_tickets:
            lines.append(_ticket_line_unchanged(t))
    else:
        lines.append("_Ninguno._")
    lines.append("")

    # --- Sección sin movimiento estancado ---
    stale_action = actions_by_type.get("notify_unchanged_stale")
    stale_tickets = stale_action.tickets if stale_action else []
    lines.append(f"⏳ **Sin movimiento — más de 5 días** ({len(stale_tickets)})")
    lines.append("")
    if stale_tickets:
        capped = stale_tickets[:max_items]
        for t in capped:
            lines.append(_ticket_line_unchanged(t))
        if len(stale_tickets) > max_items:
            extra = len(stale_tickets) - max_items
            if board_url:
                lines.append(f"_... y {extra} más. [Ver tablero →]({board_url})_")
            else:
                lines.append(f"_... y {extra} más._")
        reporters = _unique_reporters(capped)
        if reporters:
            mentions = ", ".join(f"@{r}" for r in reporters)
            lines.append(
                f"_{mentions}: ¿estos tickets siguen siendo necesarios? "
                f"Si aplica, actualizar el estado en Jira._"
            )
    else:
        lines.append("_Ninguno._")

    return title, "\n".join(lines).rstrip()


def _ticket_line_changes(t: TicketFacts) -> str:
    tags = _tags(t)
    reporter = f"@{t.reporter}" if t.reporter else "sin informador"
    return f"- [{t.key}]({t.url}) {tags}— {t.summary}\n  {t.status} | {reporter}"


def _ticket_line_unchanged(t: TicketFacts) -> str:
    tags = _tags(t)
    days_label = "–" if t.days_without_status_change == 999 else f"{t.days_without_status_change}d"
    reporter = f"@{t.reporter}" if t.reporter else "sin informador"
    return f"- [{t.key}]({t.url}) {tags}— {t.summary}\n  {t.status} · {days_label} | {reporter}"


def _tags(t: TicketFacts) -> str:
    parts = []
    if t.created_since_last_message:
        parts.append("🆕")
    if t.finalized_since_last_message:
        parts.append("✅")
    if (t.criticality or "").lower() == "highest":
        parts.append("🚨")
    return (" ".join(parts) + " ") if parts else ""



def build_weekly_cpo_message(
    project_label: str,
    active_facts: List[TicketFacts],
    resolved_this_week: List[JiraTicket],
    week_start: date,
    week_end: date,
    recurring_patterns: Optional[List] = None,
) -> str:
    week_start_str = week_start.isoformat()

    # ── Bloque 1: Resumen ejecutivo ──────────────────────────────────────────
    active_at_end = sum(1 for f in active_facts if f.status_category.lower() != "done")

    created_this_week = [f for f in active_facts if f.created[:10] >= week_start_str]
    created_count = len(created_this_week) + sum(
        1 for t in resolved_this_week if t.created[:10] >= week_start_str
    )

    resolved_count = len(resolved_this_week)

    # active_at_start = tickets that existed before monday and were not done then
    # = (active now and created before monday) + (resolved this week and created before monday)
    active_at_start = (
        sum(1 for f in active_facts if f.created[:10] < week_start_str and f.status_category.lower() != "done")
        + sum(1 for t in resolved_this_week if t.created[:10] < week_start_str)
    )

    # No movement = active, existed before monday, no status change this week
    no_movement_facts = [
        f for f in active_facts
        if f.status_category.lower() != "done"
        and f.created[:10] < week_start_str
        and f.last_status_change_at[:10] < week_start_str
    ]
    no_movement_count = len(no_movement_facts)

    highest_at_end = [
        f for f in active_facts
        if (f.criticality or "").lower() == "highest" and f.status_category.lower() != "done"
    ]

    lines: List[str] = []
    lines.append(f"📊 **Reporte semanal — {project_label}**")
    lines.append(f"_Semana {week_start_str} → {week_end.isoformat()}_")
    lines.append("")
    lines.append(
        f"Activos al inicio: **{active_at_start}** | Activos al cierre: **{active_at_end}** | "
        f"Creados: **{created_count}** | Resueltos: **{resolved_count}** | "
        f"Sin movimiento: **{no_movement_count}** | Críticos Highest al cierre: **{len(highest_at_end)}**"
    )
    lines.append("")

    # ── Bloque 2: Velocidad ──────────────────────────────────────────────────
    lines.append("**⚡ Velocidad del equipo**")

    resolution_days = []
    for t in resolved_this_week:
        try:
            fin_date = date.fromisoformat(t.last_status_change_at[:10])
            created_date = date.fromisoformat(t.created[:10])
            resolution_days.append((fin_date - created_date).days)
        except (ValueError, IndexError):
            pass

    if resolution_days:
        avg_days = sum(resolution_days) / len(resolution_days)
        lines.append(f"- Tiempo promedio de resolución: **{avg_days:.1f} días** ({len(resolution_days)} tickets)")
    else:
        lines.append("- Sin tickets resueltos esta semana.")

    # Tickets that advanced state = existed before monday, still active, changed status this week
    advanced_by_vertical: Dict[str, int] = {}
    for f in active_facts:
        if (
            f.status_category.lower() != "done"
            and f.created[:10] < week_start_str
            and f.last_status_change_at[:10] >= week_start_str
        ):
            advanced_by_vertical[f.vertical] = advanced_by_vertical.get(f.vertical, 0) + 1

    if advanced_by_vertical:
        lines.append("- Tickets que avanzaron de estado:")
        for vertical, count in sorted(advanced_by_vertical.items(), key=lambda x: -x[1]):
            lines.append(f"  - **{vertical}**: {count}")
    else:
        lines.append("- Sin tickets que avanzaron de estado esta semana.")

    # No movement by vertical
    no_movement_by_vertical: Dict[str, int] = {}
    for f in no_movement_facts:
        no_movement_by_vertical[f.vertical] = no_movement_by_vertical.get(f.vertical, 0) + 1

    if no_movement_by_vertical:
        lines.append("- Sin movimiento toda la semana por vertical:")
        for vertical, count in sorted(no_movement_by_vertical.items(), key=lambda x: -x[1]):
            lines.append(f"  - **{vertical}**: {count}")

    lines.append("")

    # ── Bloque 3: Patrones recurrentes ───────────────────────────────────────
    if recurring_patterns:
        lines.append("**🔁 Patrones recurrentes**")
        for p in recurring_patterns:
            keys_str = ", ".join(p.ticket_keys)
            lines.append(f"- **{p.label}** ({p.count} tickets: {keys_str})")
            lines.append(f"  → _{p.recommendation}_")
        lines.append("")

    # ── Bloque 4: Señales para el roadmap ────────────────────────────────────
    lines.append("**💡 Señales para el roadmap**")

    stale_by_vertical: Dict[str, int] = {}
    for f in active_facts:
        if f.is_stale and f.status_category.lower() != "done":
            stale_by_vertical[f.vertical] = stale_by_vertical.get(f.vertical, 0) + 1
    if stale_by_vertical:
        top_v = max(stale_by_vertical, key=lambda v: stale_by_vertical[v])
        lines.append(f"- Vertical con mayor carga estancada al cierre: **{top_v}** ({stale_by_vertical[top_v]} tickets)")

    if highest_at_end:
        h_verticals = list(dict.fromkeys(f.vertical for f in highest_at_end))
        lines.append(f"- Criticidad Highest activa en: {', '.join(f'**{v}**' for v in h_verticals)}")

    stale_facts = [f for f in active_facts if f.is_stale and f.days_without_status_change != 999]
    if stale_facts:
        max_days = max(f.days_without_status_change for f in stale_facts)
        if max_days > 30:
            lines.append(f"- Hay tickets sin movimiento hace más de {max_days} días — revisar si siguen siendo relevantes")

    return "\n".join(lines)


def _unique_reporters(tickets: List[TicketFacts]) -> List[str]:
    seen: List[str] = []
    for t in tickets:
        if t.reporter and t.reporter not in seen:
            seen.append(t.reporter)
    return seen


def _format_last_run(last_run_at: Optional[str]) -> str:
    if not last_run_at:
        return "el último mensaje"
    try:
        last = datetime.fromisoformat(last_run_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_days = (now.date() - last.date()).days
        if delta_days >= 2:
            return f"el {last.strftime('%d/%m')}"
        if delta_days == 1:
            return "ayer"
        minutes = int((now - last).total_seconds() / 60)
        if minutes < 60:
            return f"hace {minutes} min"
        hours = minutes // 60
        return f"hace {hours}h"
    except ValueError:
        return "el último mensaje"
