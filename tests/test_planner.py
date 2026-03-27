from datetime import datetime, timedelta, timezone

from models import TicketFacts
from planner import build_vertical_plan


def _days_ago_str(n: int) -> str:
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
        labels=["eze-team"],
        created_today=False,
        finalized_today=False,
        created_since_last_message=False,
        finalized_since_last_message=False,
        is_stale=False,
        days_without_status_change=3,
        changed_since_last_run=False,
        status_changed=False,
        assignee_changed=False,
    )
    defaults.update(kwargs)
    return TicketFacts(**defaults)


# --- notify_changes ---

def test_status_changed_goes_to_notify_changes():
    ticket = _make_facts(status_changed=True, days_without_status_change=2)
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_changes" in types
    changes = next(a for a in plan.actions if a.action_type == "notify_changes")
    assert ticket in changes.tickets


def test_created_today_goes_to_notify_changes():
    ticket = _make_facts(created_since_last_message=True, days_without_status_change=0)
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_changes" in types


def test_finalized_today_goes_to_notify_changes():
    ticket = _make_facts(
        finalized_since_last_message=True,
        status_category="done",
        days_without_status_change=0,
    )
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_changes" in types


# --- notify_unchanged_recent ---

def test_unchanged_under_5_days_goes_to_recent():
    ticket = _make_facts(days_without_status_change=3, is_stale=False)
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_unchanged_recent" in types
    recent = next(a for a in plan.actions if a.action_type == "notify_unchanged_recent")
    assert ticket in recent.tickets


# --- notify_unchanged_stale ---

def test_unchanged_5_days_goes_to_stale():
    ticket = _make_facts(days_without_status_change=5, is_stale=True)
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_unchanged_stale" in types
    stale = next(a for a in plan.actions if a.action_type == "notify_unchanged_stale")
    assert ticket in stale.tickets


# --- exclusión mutua ---

def test_notify_changes_ticket_not_in_unchanged_buckets():
    ticket = _make_facts(status_changed=True, days_without_status_change=6, is_stale=True)
    plan = build_vertical_plan("verification", [ticket])
    types = [a.action_type for a in plan.actions]
    assert "notify_changes" in types
    assert "notify_unchanged_stale" not in types
    assert "notify_unchanged_recent" not in types


# --- done tickets ---

def test_done_ticket_without_finalized_today_is_excluded():
    ticket = _make_facts(status_category="done", finalized_since_last_message=False)
    plan = build_vertical_plan("verification", [ticket])
    all_tickets = [t for a in plan.actions for t in a.tickets]
    assert ticket not in all_tickets


def test_finalized_today_done_ticket_is_included():
    ticket = _make_facts(
        status_category="done",
        finalized_since_last_message=True,
        days_without_status_change=0,
    )
    plan = build_vertical_plan("verification", [ticket])
    all_tickets = [t for a in plan.actions for t in a.tickets]
    assert ticket in all_tickets


# --- ordenamiento stale ---

def test_stale_sorted_critical_first_then_oldest():
    critical = _make_facts(key="PS-001", criticality="highest", days_without_status_change=6, is_stale=True)
    old = _make_facts(key="PS-002", criticality="", days_without_status_change=20, is_stale=True)
    recent_stale = _make_facts(key="PS-003", criticality="", days_without_status_change=8, is_stale=True)
    plan = build_vertical_plan("verification", [old, recent_stale, critical])
    stale = next(a for a in plan.actions if a.action_type == "notify_unchanged_stale")
    keys = [t.key for t in stale.tickets]
    assert keys[0] == "PS-001"   # crítico primero
    assert keys[1] == "PS-002"   # más viejo segundo
    assert keys[2] == "PS-003"   # menos viejo tercero


# --- ordenamiento recent ---

def test_recent_sorted_by_days_asc():
    older = _make_facts(key="PS-001", days_without_status_change=4, is_stale=False)
    newer = _make_facts(key="PS-002", days_without_status_change=1, is_stale=False)
    plan = build_vertical_plan("verification", [older, newer])
    recent = next(a for a in plan.actions if a.action_type == "notify_unchanged_recent")
    keys = [t.key for t in recent.tickets]
    assert keys == ["PS-002", "PS-001"]   # más reciente primero (días asc)


# --- old action types no longer emitted ---

def test_old_action_types_not_emitted():
    ticket = _make_facts(created_since_last_message=True, days_without_status_change=0)
    plan = build_vertical_plan("verification", [ticket])
    old_types = {"notify_created_today", "notify_finished_today", "notify_status_changed", "notify_stale_tickets"}
    emitted = {a.action_type for a in plan.actions}
    assert emitted.isdisjoint(old_types)
