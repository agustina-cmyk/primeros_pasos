import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import WeeklyTicketSnapshot


def _snap(status="To Do", status_category="new", days=2, stale=False,
          criticality=None, vertical="verification", reporter="ana",
          created="2026-03-15T10:00:00.000+0000", finalized_today=False) -> WeeklyTicketSnapshot:
    return WeeklyTicketSnapshot(
        status=status, status_category=status_category,
        days_without_status_change=days, is_stale=stale,
        criticality=criticality, vertical=vertical, reporter=reporter,
        created=created, finalized_today=finalized_today,
    )


def test_build_weekly_cpo_message_empty_buffer():
    from message_builder import build_weekly_cpo_message
    result = build_weekly_cpo_message("PS", {})
    assert "Sin datos acumulados" in result


def test_build_weekly_cpo_message_contains_project_label():
    from message_builder import build_weekly_cpo_message
    buffer = {"2026-03-18": {"PS-1": _snap()}}
    result = build_weekly_cpo_message("MyProject", buffer)
    assert "MyProject" in result


def test_build_weekly_cpo_message_counts_resolved_tickets():
    from message_builder import build_weekly_cpo_message
    buffer = {
        "2026-03-18": {"PS-1": _snap(), "PS-2": _snap()},
        "2026-03-19": {
            "PS-1": _snap(),
            "PS-2": _snap(status="Done", status_category="done", finalized_today=True),
        },
    }
    result = build_weekly_cpo_message("PS", buffer)
    assert "1" in result   # 1 ticket resolved


def test_build_weekly_cpo_message_detects_created_tickets():
    from message_builder import build_weekly_cpo_message
    buffer = {
        "2026-03-18": {"PS-1": _snap()},
        "2026-03-19": {"PS-1": _snap(), "PS-99": _snap()},  # PS-99 is new
    }
    result = build_weekly_cpo_message("PS", buffer)
    assert "1" in result   # 1 ticket created during the week


def test_build_weekly_cpo_message_detects_no_movement_tickets():
    from message_builder import build_weekly_cpo_message
    buffer = {
        "2026-03-18": {"PS-1": _snap(status="To Do"), "PS-2": _snap(status="In Progress")},
        "2026-03-19": {"PS-1": _snap(status="To Do"), "PS-2": _snap(status="In Progress")},
        "2026-03-20": {"PS-1": _snap(status="To Do"), "PS-2": _snap(status="In Progress")},
    }
    result = build_weekly_cpo_message("PS", buffer)
    assert "2" in result   # both tickets had no movement


def test_build_weekly_cpo_message_detects_advanced_tickets():
    from message_builder import build_weekly_cpo_message
    buffer = {
        "2026-03-18": {"PS-1": _snap(status="To Do")},
        "2026-03-19": {"PS-1": _snap(status="In Progress")},  # advanced
    }
    result = build_weekly_cpo_message("PS", buffer)
    assert "In Progress" in result or "1" in result


def test_build_weekly_cpo_message_calculates_time_to_resolve():
    from message_builder import build_weekly_cpo_message
    # Created 2026-03-15, resolved 2026-03-19 → 4 days
    buffer = {
        "2026-03-18": {"PS-1": _snap(created="2026-03-15T10:00:00.000+0000")},
        "2026-03-19": {"PS-1": _snap(
            status="Done", status_category="done",
            created="2026-03-15T10:00:00.000+0000",
            finalized_today=True,
        )},
    }
    result = build_weekly_cpo_message("PS", buffer)
    assert "4" in result   # 4 days to resolve


def test_build_weekly_cpo_message_includes_patterns():
    from message_builder import build_weekly_cpo_message
    from unittest.mock import MagicMock
    pattern = MagicMock()
    pattern.label = "Login failures"
    pattern.count = 3
    pattern.ticket_keys = ["PS-1", "PS-2", "PS-3"]
    pattern.recommendation = "Fix the auth service"
    buffer = {"2026-03-18": {"PS-1": _snap()}}
    result = build_weekly_cpo_message("PS", buffer, recurring_patterns=[pattern])
    assert "Login failures" in result
    assert "Fix the auth service" in result
