from datetime import datetime, timedelta, timezone

from message_builder import build_vertical_message
from models import AgentAction, TicketFacts, VerticalPlan


def _days_ago_str(n):
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def _make_facts(**kwargs) -> TicketFacts:
    defaults = dict(
        key="PS-001",
        vertical="verification",
        summary="Test ticket",
        status="Tareas por hacer",
        status_category="new",
        assignee=None,
        reporter="reporter",
        created=_days_ago_str(3),
        updated=_days_ago_str(1),
        last_status_change_at=_days_ago_str(3),
        description="",
        section="",
        criticality="",
        environment="",
        ticket_type="Bug",
        url="https://jira/PS-001",
        labels=[],
        created_today=False,
        finalized_today=False,
        created_since_last_message=False,
        finalized_since_last_message=False,
        is_stale=False,
        days_without_status_change=3,
        status_changed=False,
        assignee_changed=False,
    )
    defaults.update(kwargs)
    return TicketFacts(**defaults)


def _make_plan(vertical="verification", actions=None) -> VerticalPlan:
    return VerticalPlan(vertical=vertical, actions=actions or [])


def _make_action(action_type, tickets) -> AgentAction:
    return AgentAction(action_type=action_type, vertical="verification", reason="", tickets=tickets)


# --- Título ---

def test_title_shows_status_distribution():
    ticket = _make_facts(status="In Progress", status_category="indeterminate")
    plan = _make_plan(actions=[_make_action("notify_unchanged_recent", [ticket])])
    title, _ = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "WIP: 1" in title
    assert "New In: 0" in title
    assert "New Out: 0" in title
    assert "PS Daily Update" in title


def test_title_no_done_tickets():
    done = _make_facts(status="Done", status_category="done", finalized_today=False)
    plan = _make_plan(actions=[_make_action("notify_unchanged_recent", [done])])
    title, _ = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "WIP: 0" in title


def test_title_no_active_tickets_shows_fallback():
    plan = _make_plan(actions=[])
    title, _ = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "WIP: 0" in title
    assert "New In: 0" in title
    assert "New Out: 0" in title


# --- Sección cambios ---

def test_changes_section_header_present():
    ticket = _make_facts(status_changed=True)
    plan = _make_plan(actions=[_make_action("notify_changes", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "🔄" in body
    assert "Cambios desde" in body


def test_changes_section_shows_new_tag_for_created_today():
    ticket = _make_facts(created_since_last_message=True)
    plan = _make_plan(actions=[_make_action("notify_changes", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "🆕" in body


def test_changes_section_shows_finalized_tag_and_reporter_mention():
    ticket = _make_facts(finalized_since_last_message=True, status_category="done", reporter="agus")
    plan = _make_plan(actions=[_make_action("notify_changes", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "✅" in body
    assert "@agus" in body
    assert "cerrados hoy" in body


def test_changes_section_empty_state():
    plan = _make_plan(actions=[])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "Sin cambios" in body


# --- Sección recent ---

def test_recent_section_shows_days():
    ticket = _make_facts(days_without_status_change=3)
    plan = _make_plan(actions=[_make_action("notify_unchanged_recent", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "📋" in body
    assert "3d" in body


def test_recent_section_empty_state():
    plan = _make_plan(actions=[])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "Ninguno" in body or "Sin movimiento" in body


def test_recent_section_no_reporter_mention():
    ticket = _make_facts(days_without_status_change=2, reporter="user1")
    plan = _make_plan(actions=[_make_action("notify_unchanged_recent", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "¿estos tickets siguen siendo necesarios?" not in body


# --- Sección stale ---

def test_stale_section_shows_days():
    ticket = _make_facts(days_without_status_change=10)
    plan = _make_plan(actions=[_make_action("notify_unchanged_stale", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "⏳" in body
    assert "10d" in body


def test_stale_section_sentinel_shows_dash():
    ticket = _make_facts(days_without_status_change=999)
    plan = _make_plan(actions=[_make_action("notify_unchanged_stale", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "999d" not in body
    assert "–" in body


def test_stale_section_cap_with_board_link():
    tickets = [_make_facts(key=f"PS-{i:03d}", days_without_status_change=i + 5) for i in range(25)]
    plan = _make_plan(actions=[_make_action("notify_unchanged_stale", tickets)])
    _, body = build_vertical_message("PS", plan, board_url="https://jira.example.com/board", max_items=20)
    assert "Ver tablero" in body
    assert "https://jira.example.com/board" in body
    assert "5 más" in body


def test_stale_section_no_link_when_no_board_url():
    tickets = [_make_facts(key=f"PS-{i:03d}", days_without_status_change=i + 5) for i in range(25)]
    plan = _make_plan(actions=[_make_action("notify_unchanged_stale", tickets)])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "Ver tablero" not in body


def test_stale_reporter_mention():
    ticket = _make_facts(days_without_status_change=10, reporter="agus")
    plan = _make_plan(actions=[_make_action("notify_unchanged_stale", [ticket])])
    _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
    assert "¿estos tickets siguen siendo necesarios?" in body
    assert "@agus" in body
