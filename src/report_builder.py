import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from models import VerticalPlan

_ACTION_LABELS = {
    "notify_created_today": ("🆕", "Creados hoy", "#2563eb", "#eff6ff"),
    "notify_finished_today": ("✅", "Finalizados hoy", "#16a34a", "#f0fdf4"),
    "notify_stale_tickets": ("🔴", "Estancados", "#dc2626", "#fef2f2"),
}

_STATUS_COLORS = {
    "done": "#16a34a",
    "in progress": "#2563eb",
    "to do": "#6b7280",
}


def build_html_report(
    project_label: str,
    plans: Dict[str, VerticalPlan],
    outbound_messages: List[Tuple[str, str, str]],
    cpo_body: Optional[str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    # Aggregate stats from plans
    all_tickets = [t for plan in plans.values() for action in plan.actions for t in action.tickets]
    created_today = sum(1 for t in all_tickets if t.created_today)
    finalized_today = sum(1 for t in all_tickets if t.finalized_today)
    stale = sum(1 for t in all_tickets if t.is_stale)
    highest = sum(1 for t in all_tickets if (t.criticality or "").lower() == "highest")
    active = sum(1 for t in all_tickets if t.status_category.lower() != "done")

    verticals_html = _build_verticals(plans, outbound_messages)
    cpo_html = _build_cpo_section(cpo_body) if cpo_body else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Jira Agent Report — {project_label}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f1f5f9;
      color: #1e293b;
      font-size: 14px;
      line-height: 1.6;
    }}

    /* ── Header ── */
    .header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
      color: #fff;
      padding: 32px 40px 28px;
    }}
    .header-top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
    .header h1 span {{ color: #93c5fd; }}
    .header-meta {{ font-size: 12px; color: #94a3b8; margin-top: 4px; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15);
      border-radius: 20px; padding: 4px 12px; font-size: 12px; color: #e2e8f0;
      white-space: nowrap;
    }}

    /* ── Stats bar ── */
    .stats {{
      display: flex; flex-wrap: wrap; gap: 1px;
      background: #e2e8f0;
      border-bottom: 1px solid #e2e8f0;
    }}
    .stat {{
      flex: 1; min-width: 140px;
      background: #fff;
      padding: 18px 24px;
      display: flex; flex-direction: column; gap: 4px;
    }}
    .stat-value {{ font-size: 28px; font-weight: 700; line-height: 1; }}
    .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: #64748b; }}
    .stat.danger .stat-value {{ color: #dc2626; }}
    .stat.warning .stat-value {{ color: #d97706; }}
    .stat.success .stat-value {{ color: #16a34a; }}
    .stat.info .stat-value {{ color: #2563eb; }}

    /* ── Layout ── */
    .main {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
    .section-title {{
      font-size: 13px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.8px; color: #64748b;
      margin-bottom: 16px; padding-bottom: 8px;
      border-bottom: 2px solid #e2e8f0;
    }}

    /* ── Vertical grid ── */
    .verticals-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      margin-bottom: 36px;
    }}
    .vertical-card {{
      background: #fff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .vertical-header {{
      padding: 14px 18px;
      background: #f8fafc;
      border-bottom: 1px solid #e2e8f0;
      display: flex; align-items: center; justify-content: space-between;
    }}
    .vertical-name {{ font-weight: 700; font-size: 15px; }}
    .vertical-counts {{ display: flex; gap: 8px; }}
    .pill {{
      font-size: 11px; font-weight: 600; padding: 2px 8px;
      border-radius: 10px; white-space: nowrap;
    }}

    /* ── Action sections ── */
    .action-section {{ padding: 14px 18px; border-bottom: 1px solid #f1f5f9; }}
    .action-section:last-child {{ border-bottom: none; }}
    .action-header {{
      display: flex; align-items: center; gap: 8px;
      margin-bottom: 10px;
    }}
    .action-label {{ font-weight: 600; font-size: 13px; }}
    .action-count {{
      font-size: 11px; font-weight: 600; padding: 1px 7px;
      border-radius: 8px; margin-left: auto;
    }}

    /* ── Ticket rows ── */
    .ticket-row {{
      display: flex; align-items: flex-start; gap: 10px;
      padding: 8px 0;
      border-bottom: 1px solid #f8fafc;
    }}
    .ticket-row:last-child {{ border-bottom: none; }}
    .ticket-key {{
      font-size: 11px; font-weight: 700; font-family: monospace;
      color: #2563eb; text-decoration: none; white-space: nowrap;
      padding-top: 1px;
    }}
    .ticket-key:hover {{ text-decoration: underline; }}
    .ticket-info {{ flex: 1; min-width: 0; }}
    .ticket-summary {{ font-size: 13px; color: #1e293b; line-height: 1.4; }}
    .ticket-meta {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
    .critical-badge {{
      font-size: 10px; font-weight: 700; padding: 1px 6px;
      background: #fee2e2; color: #dc2626; border-radius: 4px;
      white-space: nowrap; flex-shrink: 0;
    }}

    /* ── CPO section ── */
    .cpo-card {{
      background: #fff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      margin-bottom: 36px;
    }}
    .cpo-header {{
      padding: 14px 20px;
      background: linear-gradient(90deg, #0f172a, #1e3a5f);
      color: #fff;
    }}
    .cpo-header h2 {{ font-size: 14px; font-weight: 600; }}
    .cpo-body {{ padding: 20px; }}

    .cpo-stat-row {{
      display: flex; flex-wrap: wrap; gap: 12px;
      margin-bottom: 24px;
    }}
    .cpo-stat-chip {{
      background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 10px 16px;
      flex: 1; min-width: 120px; text-align: center;
    }}
    .cpo-stat-chip .val {{ font-size: 22px; font-weight: 700; }}
    .cpo-stat-chip .lbl {{ font-size: 11px; color: #64748b; margin-top: 2px; }}

    .cpo-section {{ margin-bottom: 20px; }}
    .cpo-section h3 {{
      font-size: 13px; font-weight: 600; margin-bottom: 10px;
      padding-bottom: 6px; border-bottom: 1px solid #f1f5f9;
    }}

    .pattern-card {{
      background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #7c3aed;
      border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;
    }}
    .pattern-label {{ font-weight: 600; font-size: 13px; color: #1e293b; }}
    .pattern-keys {{ font-size: 11px; color: #64748b; margin: 4px 0; font-family: monospace; }}
    .pattern-rec {{
      font-size: 12px; color: #475569; margin-top: 6px;
      padding-top: 6px; border-top: 1px solid #e2e8f0;
    }}
    .pattern-rec::before {{ content: "→ "; color: #7c3aed; font-weight: 700; }}

    .stale-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    .stale-table th {{
      text-align: left; padding: 6px 10px;
      background: #f8fafc; border-bottom: 2px solid #e2e8f0;
      font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b;
    }}
    .stale-table td {{ padding: 8px 10px; border-bottom: 1px solid #f1f5f9; }}
    .stale-table tr:last-child td {{ border-bottom: none; }}
    .stale-table a {{ color: #2563eb; text-decoration: none; font-weight: 600; font-family: monospace; }}
    .stale-table a:hover {{ text-decoration: underline; }}
    .age-chip {{
      display: inline-block; font-size: 11px; font-weight: 600;
      padding: 1px 7px; border-radius: 10px;
    }}
    .age-high {{ background: #fee2e2; color: #dc2626; }}
    .age-mid  {{ background: #fef3c7; color: #d97706; }}
    .age-low  {{ background: #f1f5f9; color: #64748b; }}

    .vertical-row {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 7px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px;
    }}
    .vertical-row:last-child {{ border-bottom: none; }}

    .no-changes {{
      text-align: center; padding: 32px; color: #94a3b8;
      font-style: italic; font-size: 13px;
    }}

    /* ── Footer ── */
    .footer {{
      text-align: center; padding: 20px; color: #94a3b8;
      font-size: 12px; border-top: 1px solid #e2e8f0; margin-top: 8px;
    }}
  </style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div>
      <h1>Jira Agent Report — <span>{project_label}</span></h1>
      <div class="header-meta">Generado el {now} · Dry-run (no enviado a Roam)</div>
    </div>
    <div class="badge">🔍 Dry-run</div>
  </div>
</div>

<div class="stats">
  <div class="stat info">
    <div class="stat-value">{active}</div>
    <div class="stat-label">Tickets activos</div>
  </div>
  <div class="stat danger">
    <div class="stat-value">{stale}</div>
    <div class="stat-label">Estancados</div>
  </div>
  <div class="stat danger">
    <div class="stat-value">{highest}</div>
    <div class="stat-label">Criticidad Highest</div>
  </div>
  <div class="stat success">
    <div class="stat-value">{finalized_today}</div>
    <div class="stat-label">Finalizados hoy</div>
  </div>
  <div class="stat info">
    <div class="stat-value">{created_today}</div>
    <div class="stat-label">Creados hoy</div>
  </div>
</div>

<div class="main">
  {cpo_html}

  <div class="section-title">Mensajes por vertical ({len(outbound_messages)} canales)</div>
  {"<div class='verticals-grid'>" + verticals_html + "</div>" if outbound_messages else "<div class='no-changes'>Sin cambios relevantes para comunicar en esta corrida.</div>"}
</div>

<div class="footer">
  Jira Agent · Dry-run report · {now}
</div>

</body>
</html>"""


def _build_verticals(
    plans: Dict[str, VerticalPlan],
    outbound_messages: List[Tuple[str, str, str]],
) -> str:
    verticals_with_messages = {v for v, _, _ in outbound_messages}
    html_parts = []
    for vertical, _, _ in outbound_messages:
        plan = plans.get(vertical)
        if not plan:
            continue
        html_parts.append(_vertical_card(plan, vertical in verticals_with_messages))
    return "\n".join(html_parts)


def _vertical_card(plan: VerticalPlan, has_message: bool) -> str:
    counts = {a.action_type: len(a.tickets) for a in plan.actions}
    pills = []
    for action_type, (emoji, label, color, _) in _ACTION_LABELS.items():
        n = counts.get(action_type, 0)
        if n:
            pills.append(
                f'<span class="pill" style="background:{_ACTION_LABELS[action_type][3]};'
                f'color:{_ACTION_LABELS[action_type][2]}">{emoji} {n}</span>'
            )

    actions_html = "".join(_action_section(a) for a in plan.actions if a.tickets)

    return f"""
<div class="vertical-card">
  <div class="vertical-header">
    <span class="vertical-name">{plan.vertical}</span>
    <div class="vertical-counts">{"".join(pills)}</div>
  </div>
  {actions_html or "<div class='no-changes'>Sin novedades</div>"}
</div>"""


def _action_section(action) -> str:
    emoji, label, color, bg = _ACTION_LABELS.get(
        action.action_type, ("📋", action.action_type, "#64748b", "#f8fafc")
    )
    tickets_html = "".join(_ticket_row(t) for t in action.tickets[:20])
    overflow = len(action.tickets) - 20
    overflow_html = (
        f'<div style="font-size:11px;color:#94a3b8;padding:6px 0">… y {overflow} más</div>'
        if overflow > 0 else ""
    )
    return f"""
<div class="action-section">
  <div class="action-header">
    <span style="font-size:16px">{emoji}</span>
    <span class="action-label" style="color:{color}">{label}</span>
    <span class="action-count" style="background:{bg};color:{color}">{len(action.tickets)}</span>
  </div>
  {tickets_html}
  {overflow_html}
</div>"""


def _ticket_row(ticket) -> str:
    is_critical = (ticket.criticality or "").lower() == "highest"
    critical_html = '<span class="critical-badge">🚨 Highest</span>' if is_critical else ""
    reporter = f"@{ticket.reporter}" if ticket.reporter else "—"
    status_color = _STATUS_COLORS.get(ticket.status_category.lower(), "#6b7280")
    return f"""
<div class="ticket-row">
  <a class="ticket-key" href="{ticket.url}" target="_blank">{ticket.key}</a>
  <div class="ticket-info">
    <div class="ticket-summary">{ticket.summary}</div>
    <div class="ticket-meta">
      <span style="color:{status_color};font-weight:600">{ticket.status}</span>
      · {reporter}
    </div>
  </div>
  {critical_html}
</div>"""


def _build_cpo_section(cpo_body: str) -> str:
    lines = cpo_body.splitlines()

    stats_line = next((l for l in lines if "Total activos" in l), "")
    stats = _parse_stats_line(stats_line)

    vertical_rows = _extract_vertical_rows(lines)
    stale_rows = _extract_stale_rows(lines)
    patterns = _extract_patterns(lines)
    roadmap = _extract_roadmap(lines)

    stats_html = "".join(
        f'<div class="cpo-stat-chip"><div class="val">{v}</div><div class="lbl">{k}</div></div>'
        for k, v in stats
    )

    verticals_html = "".join(
        f'<div class="vertical-row"><span><strong>{name}</strong></span><span style="color:#64748b;font-size:12px">{detail}</span></div>'
        for name, detail in vertical_rows
    )

    stale_html = "".join(
        f'<tr><td><a href="{url}" target="_blank">{key}</a></td>'
        f'<td>{vertical}</td>'
        f'<td>{summary}</td>'
        f'<td><span class="age-chip {_age_class(days)}">{days}d</span></td></tr>'
        for key, url, vertical, summary, days in stale_rows
    )

    patterns_html = "".join(
        f'<div class="pattern-card">'
        f'<div class="pattern-label">{label}</div>'
        f'<div class="pattern-keys">{keys}</div>'
        f'<div class="pattern-rec">{rec}</div>'
        f'</div>'
        for label, keys, rec in patterns
    )

    roadmap_html = "".join(
        f'<div style="padding:5px 0;font-size:13px;border-bottom:1px solid #f1f5f9">💡 {item}</div>'
        for item in roadmap
    )

    return f"""
<div class="cpo-card">
  <div class="cpo-header"><h2>📊 Análisis CPO del tablero</h2></div>
  <div class="cpo-body">

    <div class="cpo-stat-row">{stats_html}</div>

    {"<div class='cpo-section'><h3>Por vertical</h3>" + verticals_html + "</div>" if verticals_html else ""}

    {"<div class='cpo-section'><h3>⏳ Tickets sin movimiento más prolongado</h3><table class='stale-table'><thead><tr><th>Ticket</th><th>Vertical</th><th>Resumen</th><th>Días</th></tr></thead><tbody>" + stale_html + "</tbody></table></div>" if stale_html else ""}

    {"<div class='cpo-section'><h3>🔁 Patrones recurrentes</h3>" + patterns_html + "</div>" if patterns_html else ""}

    {"<div class='cpo-section'><h3>💡 Señales para el roadmap</h3>" + roadmap_html + "</div>" if roadmap_html else ""}

  </div>
</div>"""


# ── Parsers for the markdown CPO body ──────────────────────────────────────

def _parse_stats_line(line: str) -> List[Tuple[str, str]]:
    result = []
    for part in re.split(r"\|", line):
        part = part.strip().replace("**", "")
        m = re.match(r"(.+?):\s*(\d+)", part)
        if m:
            result.append((m.group(1).strip(), m.group(2).strip()))
    return result


def _extract_vertical_rows(lines: List[str]) -> List[Tuple[str, str]]:
    rows = []
    in_section = False
    for line in lines:
        if "**Por vertical**" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("**") or line.startswith("##"):
                break
            m = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
            if m:
                rows.append((m.group(1), m.group(2)))
    return rows


def _extract_stale_rows(lines: List[str]) -> List[Tuple[str, str, str, str, str]]:
    rows = []
    in_section = False
    for line in lines:
        if "sin movimiento más prolongado" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("**") and "sin movimiento" not in line:
                break
            m = re.match(r"- \[(.+?)\]\((.+?)\)\s+\((.+?)\)\s+[—–]\s*(\d+)d\s*·\s*(.+)", line)
            if m:
                rows.append((m.group(1), m.group(2), m.group(3), m.group(5).rstrip("🚨").strip(), m.group(4)))
    return rows


def _extract_patterns(lines: List[str]) -> List[Tuple[str, str, str]]:
    patterns = []
    in_section = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if "Patrones recurrentes" in line:
            in_section = True
            i += 1
            continue
        if in_section:
            if line.startswith("**") and "Patrones" not in line:
                break
            m = re.match(r"- \*\*(.+?)\*\*\s+\((\d+) tickets?: (.+?)\)", line)
            if m:
                label = m.group(1)
                keys = m.group(3)
                rec = ""
                if i + 1 < len(lines):
                    rec_m = re.match(r"\s*→\s*_(.+)_", lines[i + 1])
                    if rec_m:
                        rec = rec_m.group(1)
                        i += 1
                patterns.append((label, keys, rec))
        i += 1
    return patterns


def _extract_roadmap(lines: List[str]) -> List[str]:
    items = []
    in_section = False
    for line in lines:
        if "Señales para el roadmap" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("**"):
                break
            m = re.match(r"- (.+)", line)
            if m:
                items.append(m.group(1))
    return items


def _age_class(days: str) -> str:
    try:
        d = int(days)
        if d >= 30:
            return "age-high"
        if d >= 15:
            return "age-mid"
        return "age-low"
    except ValueError:
        return "age-low"
