import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import AgentMemoryState, WeeklyTicketSnapshot


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
