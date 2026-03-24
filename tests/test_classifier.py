from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from classifier import classify_tickets
from jira_client import JiraTicket
from models import AgentMemoryState, RoadmapMemoryState


def _days_ago_str(n: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def _make_ticket(**kwargs) -> JiraTicket:
    defaults = dict(
        key="PS-001",
        summary="Test ticket",
        labels=["eze-team"],
        status="Tareas por hacer",
        status_category="new",
        assignee=None,
        reporter="reporter",
        created=_days_ago_str(10),
        updated=_days_ago_str(1),
        last_status_change_at=_days_ago_str(10),
        description="",
        section="",
        criticality="",
        environment="",
        ticket_type="Bug",
        url="https://jira.example.com/PS-001",
    )
    defaults.update(kwargs)
    return JiraTicket(**defaults)


def _classify_one(**ticket_kwargs):
    ticket = _make_ticket(**ticket_kwargs)
    memory = AgentMemoryState(tickets={}, roadmap=RoadmapMemoryState())
    grouped = classify_tickets(
        tickets=[ticket],
        memory_state=memory,
        label_prefix="vertical:",
        label_to_vertical={"eze-team": "verification"},
        unchanged_stale_days=5,
    )
    facts_list = grouped.get("verification", [])
    assert len(facts_list) == 1
    return facts_list[0]


def test_days_without_status_change_from_last_status_change():
    facts = _classify_one(last_status_change_at=_days_ago_str(8))
    assert facts.days_without_status_change == 8


def test_days_without_status_change_zero_when_changed_today():
    facts = _classify_one(last_status_change_at=_days_ago_str(0))
    assert facts.days_without_status_change == 0


def test_days_without_status_change_fallback_to_created():
    facts = _classify_one(
        last_status_change_at="",
        created=_days_ago_str(12),
    )
    assert facts.days_without_status_change == 12


def test_days_without_status_change_sentinel_when_both_null():
    facts = _classify_one(last_status_change_at="", created="")
    assert facts.days_without_status_change == 999


def test_is_stale_true_when_days_gte_threshold():
    facts = _classify_one(last_status_change_at=_days_ago_str(5))
    assert facts.is_stale is True


def test_is_stale_false_when_days_lt_threshold():
    facts = _classify_one(last_status_change_at=_days_ago_str(4))
    assert facts.is_stale is False


def test_status_changed_today_field_does_not_exist():
    facts = _classify_one()
    assert not hasattr(facts, "status_changed_today")
