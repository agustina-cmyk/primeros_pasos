import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date

from models import AgentMemoryState, WeeklyTicketSnapshot


def _make_facts(**kwargs):
    from models import TicketFacts
    defaults = dict(
        key="PS-001", vertical="verification", summary="Test", status="To Do",
        status_category="new", assignee=None, reporter="ana",
        created="2026-03-15T10:00:00.000+0000", updated="2026-03-18T10:00:00.000+0000",
        last_status_change_at="2026-03-15T10:00:00.000+0000",
        description="", section="", criticality="", environment="", ticket_type="Bug",
        url="https://jira/PS-001", labels=[],
        created_today=False, finalized_today=False, is_stale=False,
        days_without_status_change=3, changed_since_last_run=False,
        status_changed=False, assignee_changed=False,
    )
    defaults.update(kwargs)
    return TicketFacts(**defaults)


def test_build_weekly_snapshot_maps_facts_to_snapshot():
    from agent import _build_weekly_snapshot
    facts = {"verification": [_make_facts(key="PS-1", status="In Progress", reporter="bob")]}
    result = _build_weekly_snapshot(facts)
    assert "PS-1" in result
    assert result["PS-1"].status == "In Progress"
    assert result["PS-1"].reporter == "bob"
    assert result["PS-1"].created == "2026-03-15T10:00:00.000+0000"


def test_build_next_weekly_buffer_appends_today():
    from agent import _build_next_weekly_buffer
    state = AgentMemoryState.empty()
    state.weekly_buffer = {"2026-03-18": {"PS-1": WeeklyTicketSnapshot(
        status="To Do", status_category="new", days_without_status_change=1,
        is_stale=False, criticality=None, vertical="v", reporter=None,
        created="2026-03-15T10:00:00.000+0000", finalized_today=False,
    )}}
    facts = {"verification": [_make_facts(key="PS-2")]}
    result = _build_next_weekly_buffer(state, "2026-03-19", facts)
    assert "2026-03-18" in result   # previous day preserved
    assert "2026-03-19" in result   # today added
    assert "PS-2" in result["2026-03-19"]


def test_build_next_weekly_buffer_clears_stale_buffer():
    from agent import _build_next_weekly_buffer
    state = AgentMemoryState.empty()
    # Put a snapshot from a different ISO week (2026-03-09 = week 11, 2026-03-24 = week 13)
    state.weekly_buffer = {"2026-03-09": {"PS-OLD": WeeklyTicketSnapshot(
        status="Done", status_category="done", days_without_status_change=5,
        is_stale=True, criticality=None, vertical="v", reporter=None,
        created="2026-03-01T10:00:00.000+0000", finalized_today=False,
    )}}
    facts = {"verification": [_make_facts(key="PS-NEW")]}
    result = _build_next_weekly_buffer(state, "2026-03-24", facts)
    assert "2026-03-09" not in result      # stale data cleared
    assert "2026-03-24" in result          # today's snapshot added
    assert "PS-NEW" in result["2026-03-24"]


def test_build_next_weekly_buffer_empty_buffer():
    from agent import _build_next_weekly_buffer
    state = AgentMemoryState.empty()
    facts = {"payments": [_make_facts(key="PS-5", vertical="payments")]}
    result = _build_next_weekly_buffer(state, "2026-03-18", facts)
    assert "2026-03-18" in result
    assert "PS-5" in result["2026-03-18"]


def test_weekly_ticket_snapshot_fields():
    snap = WeeklyTicketSnapshot(
        status="In Progress",
        status_category="indeterminate",
        days_without_status_change=3,
        is_stale=False,
        criticality="",
        vertical="verification",
        reporter="jdoe",
        created="2026-03-15T10:30:00.000+0000",
        finalized_today=False,
    )
    assert snap.status == "In Progress"
    assert snap.created == "2026-03-15T10:30:00.000+0000"
    assert snap.finalized_today is False


def test_agent_memory_state_empty_has_empty_weekly_buffer():
    state = AgentMemoryState.empty()
    assert state.weekly_buffer == {}
    assert state.weekly_last_run_at is None


def test_agent_memory_state_to_dict_includes_weekly_buffer():
    snap = WeeklyTicketSnapshot(
        status="To Do", status_category="new", days_without_status_change=1,
        is_stale=False, criticality=None, vertical="payments", reporter=None,
        created="2026-03-18T09:00:00.000+0000", finalized_today=False,
    )
    state = AgentMemoryState.empty()
    state.weekly_buffer = {"2026-03-18": {"PS-1": snap}}
    state.weekly_last_run_at = "2026-03-21T17:00:00-03:00"

    d = state.to_dict()
    assert "weekly_buffer" in d
    assert "2026-03-18" in d["weekly_buffer"]
    assert d["weekly_buffer"]["2026-03-18"]["PS-1"]["status"] == "To Do"
    assert d["weekly_last_run_at"] == "2026-03-21T17:00:00-03:00"


def test_agent_memory_load_roundtrip_weekly_buffer(tmp_path):
    import json
    from memory import AgentMemory

    state_path = tmp_path / "state.json"
    snap = WeeklyTicketSnapshot(
        status="To Do", status_category="new", days_without_status_change=2,
        is_stale=False, criticality=None, vertical="verification", reporter="ana",
        created="2026-03-18T08:00:00.000+0000", finalized_today=False,
    )
    state = AgentMemoryState.empty()
    state.weekly_buffer = {"2026-03-18": {"PS-42": snap}}
    state.weekly_last_run_at = "2026-03-21T17:00:00+00:00"

    mem = AgentMemory(str(state_path))
    mem.save(state)

    loaded = mem.load()
    assert "2026-03-18" in loaded.weekly_buffer
    loaded_snap = loaded.weekly_buffer["2026-03-18"]["PS-42"]
    assert loaded_snap.status == "To Do"
    assert loaded_snap.reporter == "ana"
    assert loaded.weekly_last_run_at == "2026-03-21T17:00:00+00:00"
