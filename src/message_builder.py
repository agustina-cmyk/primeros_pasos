from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from models import TicketFacts, VerticalPlan

_SECTION_EMOJI = {
    "notify_created_today": "🆕",
    "notify_finished_today": "✅",
    "notify_status_changed": "🔄",
    "notify_stale_tickets": "🔴",
}


def build_vertical_message(
    project_label: str,
    plan: VerticalPlan,
    channel_url: str,
    max_items: int,
    last_run_at: Optional[str] = None,
) -> Tuple[str, str]:
    counts = {action.action_type: len(action.tickets) for action in plan.actions}
    title = (
        f"[Jira Agent] {project_label} | Vertical: {plan.vertical} | "
        f"Creados hoy: {counts.get('notify_created_today', 0)} | "
        f"Finalizados hoy: {counts.get('notify_finished_today', 0)} | "
        f"Estancados: {counts.get('notify_stale_tickets', 0)}"
    )

    lines: List[str] = []

    if not plan.actions:
        lines.append("Sin cambios relevantes para comunicar en esta corrida.")
        return title, "\n".join(lines)

    # Resumen de cambios vs última corrida
    all_tickets = [t for action in plan.actions for t in action.tickets]
    changed = [t for t in all_tickets if t.status_changed]
    last_run_label = _format_last_run(last_run_at)
    if changed:
        lines.append(f"📋 **Cambios desde {last_run_label}**")
        for t in changed:
            lines.append(f"- [{t.key}]({t.url}) — {t.summary} → **{t.status}**")
    else:
        lines.append(f"📋 _Sin cambios de estado desde {last_run_label}._")
    lines.append("")

    for action in plan.actions:
        emoji = _SECTION_EMOJI.get(action.action_type, "📋")
        lines.append(f"{emoji} **{_section_title(action.action_type)}**")
        lines.append("")
        lines.extend(_render_tickets(action.action_type, action.tickets, max_items=max_items))
        lines.append("")

    return title, "\n".join(lines).rstrip()


def _section_title(action_type: str) -> str:
    return {
        "notify_created_today": "Tickets creados hoy",
        "notify_finished_today": "Tickets finalizados hoy",
        "notify_status_changed": "Cambios de estado desde la última corrida",
        "notify_stale_tickets": "Tickets estancados",
    }.get(action_type, action_type)


def _render_tickets(
    action_type: str,
    tickets: List[TicketFacts],
    max_items: int,
) -> List[str]:
    if not tickets:
        return ["_Sin tickets en esta sección._", ""]

    output: List[str] = []
    limited = tickets[:max_items]

    for ticket in limited:
        reporter = f"**@{ticket.reporter}**" if ticket.reporter else "sin informador"
        alert = " 🚨" if (ticket.criticality or "").lower() == "highest" else ""
        output.append(f"- [{ticket.key}]({ticket.url}) — {ticket.summary}{alert}")
        output.append(f"  Estado: {ticket.status} | Informador: {reporter}")

    if len(tickets) > len(limited):
        output.append(f"_... y {len(tickets) - len(limited)} más._")

    output.append("")

    # Mensaje al grupo: una sola vez por sección con todos los reporters únicos
    if action_type == "notify_stale_tickets":
        reporters = _unique_reporters(limited)
        if reporters:
            mentions = ", ".join(f"@{r}" for r in reporters)
            output.append(f"_{mentions}: ¿estos tickets siguen siendo necesarios? Si aplica, actualizar el estado en Jira._")
    elif action_type == "notify_finished_today":
        reporters = _unique_reporters(limited)
        if reporters:
            mentions = ", ".join(f"@{r}" for r in reporters)
            output.append(f"_{mentions}: sus tickets fueron cerrados hoy_ ✅")

    return output


def build_cpo_message(
    project_label: str,
    grouped_facts: Dict[str, List[TicketFacts]],
    recurring_patterns: Optional[List] = None,
) -> str:
    from datetime import date as date_type

    all_tickets = [t for tickets in grouped_facts.values() for t in tickets]
    active = [t for t in all_tickets if t.status_category.lower() != "done"]
    stale = [t for t in active if t.is_stale]
    highest = [t for t in active if (t.criticality or "").lower() == "highest"]
    created_today = [t for t in all_tickets if t.created_today]
    finalized_today = [t for t in all_tickets if t.finalized_today]

    today = datetime.now(timezone.utc).date()
    lines: List[str] = []

    lines.append(f"📊 **Análisis del tablero — {project_label}**")
    lines.append("")
    lines.append(
        f"Total activos: **{len(active)}** | Estancados: **{len(stale)}** | "
        f"Críticos (Highest): **{len(highest)}** | Creados hoy: **{len(created_today)}** | Finalizados hoy: **{len(finalized_today)}**"
    )
    lines.append("")

    # Por vertical
    lines.append("**Por vertical**")
    for vertical, tickets in sorted(grouped_facts.items()):
        v_active = [t for t in tickets if t.status_category.lower() != "done"]
        v_stale = [t for t in v_active if t.is_stale]
        v_highest = [t for t in v_active if (t.criticality or "").lower() == "highest"]
        if not v_active:
            continue
        parts = [f"{len(v_active)} activos"]
        if v_stale:
            parts.append(f"{len(v_stale)} estancados")
        if v_highest:
            parts.append(f"{len(v_highest)} críticos 🚨")
        lines.append(f"- **{vertical}**: {' · '.join(parts)}")
    lines.append("")

    # Tickets sin asignar y/o sin vertical
    unassigned = [t for t in active if not t.assignee]
    no_vertical = [t for t in active if t.vertical == "sin_vertical"]
    attention = list({t.key: t for t in unassigned + no_vertical}.values())
    if attention:
        limit = 20
        lines.append(f"**⚠️ Requieren atención ({len(attention)})**")
        for t in attention[:limit]:
            tags = []
            if not t.assignee:
                tags.append("sin asignar")
            if t.vertical == "sin_vertical":
                tags.append("sin vertical")
            alert = " 🚨" if (t.criticality or "").lower() == "highest" else ""
            lines.append(f"- [{t.key}]({t.url}) ({', '.join(tags)}) — {t.summary}{alert}")
        if len(attention) > limit:
            lines.append(f"_... y {len(attention) - limit} más._")
        lines.append("")

    # Tickets más estancados
    stale_with_age = []
    for t in stale:
        last_dt = _parse_iso(t.last_status_change_at)
        days = (today - last_dt.date()).days if last_dt else None
        stale_with_age.append((days, t))

    stale_with_age.sort(key=lambda x: x[0] if x[0] is not None else 0, reverse=True)

    lines.append("**⏳ Tickets sin movimiento más prolongado**")
    for days, t in stale_with_age[:8]:
        age_label = f"{days}d" if days is not None else "?"
        alert = " 🚨" if (t.criticality or "").lower() == "highest" else ""
        lines.append(f"- [{t.key}]({t.url}) ({t.vertical}) — {age_label} · {t.summary}{alert}")
    lines.append("")

    # Patrones recurrentes (análisis semántico)
    if recurring_patterns:
        lines.append("**🔁 Patrones recurrentes**")
        for p in recurring_patterns:
            keys_str = ", ".join(p.ticket_keys)
            lines.append(f"- **{p.label}** ({p.count} tickets: {keys_str})")
            lines.append(f"  → _{p.recommendation}_")
        lines.append("")

    # Distribución por estado
    status_count: Dict[str, int] = {}
    for t in active:
        status_count[t.status] = status_count.get(t.status, 0) + 1
    lines.append("**Distribución por estado**")
    for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
        lines.append(f"- {status}: {count}")
    lines.append("")

    # Señales para el roadmap
    lines.append("**💡 Señales para el roadmap**")
    if stale_with_age:
        top_vertical = max(
            grouped_facts,
            key=lambda v: len([t for t in grouped_facts[v] if t.is_stale and t.status_category.lower() != "done"]),
        )
        top_stale_count = len([t for t in grouped_facts[top_vertical] if t.is_stale and t.status_category.lower() != "done"])
        lines.append(f"- Vertical con más carga estancada: **{top_vertical}** ({top_stale_count} tickets)")
    if highest:
        h_verticals = list(dict.fromkeys(t.vertical for t in highest))
        lines.append(f"- Criticidad Highest activa en: {', '.join(f'**{v}**' for v in h_verticals)}")
    oldest_days = stale_with_age[0][0] if stale_with_age else None
    if oldest_days and oldest_days > 30:
        lines.append(f"- Hay tickets sin movimiento hace más de {oldest_days} días — revisar si siguen siendo relevantes")

    return "\n".join(lines)


def _parse_iso(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


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
        today = datetime.now(timezone.utc).date()
        delta = (today - last.date()).days
        if delta == 0:
            return f"hoy ({last.strftime('%H:%M')})"
        if delta == 1:
            return "ayer"
        return last.strftime("el %d/%m a las %H:%M")
    except ValueError:
        return "el último mensaje"
