from collections import Counter
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from models import TicketFacts, VerticalPlan, WeeklyTicketSnapshot


def build_vertical_message(
    project_label: str,
    plan: VerticalPlan,
    board_url: str,
    max_items: int,
    last_run_at: Optional[str] = None,
) -> Tuple[str, str]:
    # Todos los tickets del plan para el título
    all_tickets = [t for action in plan.actions for t in action.tickets]
    active = [
        t for t in all_tickets
        if t.status_category.lower() != "done" or t.finalized_today
    ]
    status_counts = Counter(t.status for t in active)
    if status_counts:
        status_summary = " · ".join(
            f"{s}: {c}"
            for s, c in status_counts.most_common()
        )
    else:
        status_summary = "Sin tickets activos"

    title = f"[Jira Agent] {project_label} | Vertical: {plan.vertical} | {status_summary}"

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
        finalized = [t for t in changes_tickets if t.finalized_today]
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
    if t.created_today:
        parts.append("🆕")
    if t.finalized_today:
        parts.append("✅")
    if (t.criticality or "").lower() == "highest":
        parts.append("🚨")
    return (" ".join(parts) + " ") if parts else ""


def build_cpo_message(
    project_label: str,
    grouped_facts: Dict[str, List[TicketFacts]],
    recurring_patterns: Optional[List] = None,
) -> str:
    all_tickets = [t for tickets in grouped_facts.values() for t in tickets]
    active = [t for t in all_tickets if t.status_category.lower() != "done"]
    stale = [t for t in active if t.is_stale]
    highest = [t for t in active if (t.criticality or "").lower() == "highest"]
    created_today = [t for t in all_tickets if t.created_today]
    finalized_today = [t for t in all_tickets if t.finalized_today]

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
    stale_with_age = [(t.days_without_status_change, t) for t in stale]
    stale_with_age.sort(key=lambda x: x[0], reverse=True)

    lines.append("**⏳ Tickets sin movimiento más prolongado**")
    for days, t in stale_with_age[:8]:
        age_label = "–" if days == 999 else f"{days}d"
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
    if oldest_days and oldest_days != 999 and oldest_days > 30:
        lines.append(f"- Hay tickets sin movimiento hace más de {oldest_days} días — revisar si siguen siendo relevantes")

    return "\n".join(lines)


def build_weekly_cpo_message(
    project_label: str,
    buffer: Dict[str, Dict[str, WeeklyTicketSnapshot]],
    recurring_patterns: Optional[List] = None,
) -> str:
    if not buffer:
        return "Sin datos acumulados para la semana."

    sorted_dates = sorted(buffer.keys())
    first_day = buffer[sorted_dates[0]]
    last_day = buffer[sorted_dates[-1]]

    # ── Bloque 1: Resumen ejecutivo ──────────────────────────────────────────
    all_keys_ever = {k for day in buffer.values() for k in day}
    first_keys = set(first_day.keys())
    last_keys = set(last_day.keys())

    active_at_start = sum(1 for s in first_day.values() if s.status_category.lower() != "done")
    active_at_end = sum(1 for s in last_day.values() if s.status_category.lower() != "done")

    # Created = present in any day but not in the first snapshot
    created_count = len(all_keys_ever - first_keys)

    # Resolved = any snapshot where finalized_today is True
    resolved_keys: set = set()
    for day_snaps in buffer.values():
        for key, snap in day_snaps.items():
            if snap.finalized_today:
                resolved_keys.add(key)
    resolved_count = len(resolved_keys)

    # No movement = present in first AND last snapshot with same status every day they appear
    no_movement_keys = set()
    for key in first_keys & last_keys:
        statuses = {
            day_snaps[key].status
            for day_snaps in buffer.values()
            if key in day_snaps
        }
        if len(statuses) == 1:
            no_movement_keys.add(key)
    no_movement_count = len(no_movement_keys)

    highest_at_end = [
        (key, snap) for key, snap in last_day.items()
        if (snap.criticality or "").lower() == "highest" and snap.status_category.lower() != "done"
    ]

    week_start = sorted_dates[0]
    week_end = sorted_dates[-1]

    lines: List[str] = []
    lines.append(f"📊 **Reporte semanal — {project_label}**")
    lines.append(f"_Semana {week_start} → {week_end}_")
    lines.append("")
    lines.append(
        f"Activos al inicio: **{active_at_start}** | Activos al cierre: **{active_at_end}** | "
        f"Creados: **{created_count}** | Resueltos: **{resolved_count}** | "
        f"Sin movimiento: **{no_movement_count}** | Críticos Highest al cierre: **{len(highest_at_end)}**"
    )
    lines.append("")

    # ── Bloque 2: Velocidad ──────────────────────────────────────────────────
    lines.append("**⚡ Velocidad del equipo**")

    # Time to resolve
    resolution_days = []
    for key in resolved_keys:
        fin_date_str = None
        created_str = None
        for date_str in sorted_dates:
            day_snaps = buffer.get(date_str, {})
            if key in day_snaps:
                if created_str is None:
                    created_str = day_snaps[key].created
                if day_snaps[key].finalized_today:
                    fin_date_str = date_str
                    break
        if fin_date_str and created_str:
            try:
                fin_date = date.fromisoformat(fin_date_str)
                created_date = date.fromisoformat(created_str[:10])
                resolution_days.append((fin_date - created_date).days)
            except (ValueError, IndexError):
                pass

    if resolution_days:
        avg_days = sum(resolution_days) / len(resolution_days)
        lines.append(f"- Tiempo promedio de resolución: **{avg_days:.1f} días** ({len(resolution_days)} tickets)")
    else:
        lines.append("- Sin tickets resueltos esta semana.")

    # Tickets that advanced state (present in first+last, status changed across any two days)
    advanced_by_vertical: Dict[str, int] = {}
    for key in first_keys & last_keys:
        statuses_seen = {
            day_snaps[key].status
            for day_snaps in buffer.values()
            if key in day_snaps
        }
        if len(statuses_seen) > 1:
            vertical = last_day[key].vertical
            advanced_by_vertical[vertical] = advanced_by_vertical.get(vertical, 0) + 1

    if advanced_by_vertical:
        lines.append("- Tickets que avanzaron de estado:")
        for vertical, count in sorted(advanced_by_vertical.items(), key=lambda x: -x[1]):
            lines.append(f"  - **{vertical}**: {count}")
    else:
        lines.append("- Sin tickets que avanzaron de estado esta semana.")

    # No movement by vertical
    no_movement_by_vertical: Dict[str, int] = {}
    for key in no_movement_keys:
        if key in last_day:
            vertical = last_day[key].vertical
            no_movement_by_vertical[vertical] = no_movement_by_vertical.get(vertical, 0) + 1

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
    active_last = {k: s for k, s in last_day.items() if s.status_category.lower() != "done"}
    if active_last:
        stale_by_vertical: Dict[str, int] = {}
        for snap in active_last.values():
            if snap.is_stale:
                stale_by_vertical[snap.vertical] = stale_by_vertical.get(snap.vertical, 0) + 1
        if stale_by_vertical:
            top_v = max(stale_by_vertical, key=lambda v: stale_by_vertical[v])
            lines.append(f"- Vertical con mayor carga estancada al cierre: **{top_v}** ({stale_by_vertical[top_v]} tickets)")
    if highest_at_end:
        h_verticals = list(dict.fromkeys(s.vertical for _, s in highest_at_end))
        lines.append(f"- Criticidad Highest activa en: {', '.join(f'**{v}**' for v in h_verticals)}")

    stale_last = [(s.days_without_status_change, k) for k, s in last_day.items() if s.is_stale]
    if stale_last:
        max_days, _ = max(stale_last, key=lambda x: x[0])
        if max_days != 999 and max_days > 30:
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
        today = datetime.now(timezone.utc).date()
        delta = (today - last.date()).days
        if delta == 0:
            return f"hoy ({last.strftime('%H:%M')})"
        if delta == 1:
            return "ayer"
        return last.strftime("el %d/%m a las %H:%M")
    except ValueError:
        return "el último mensaje"
