import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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


def test_build_next_weekly_buffer_overwrites_existing_today():
    from agent import _build_next_weekly_buffer
    state = AgentMemoryState.empty()
    state.weekly_buffer = {"2026-03-18": {"PS-OLD": WeeklyTicketSnapshot(
        status="To Do", status_category="new", days_without_status_change=1,
        is_stale=False, criticality=None, vertical="v", reporter=None,
        created="2026-03-15T10:00:00.000+0000", finalized_today=False,
    )}}
    facts = {"verification": [_make_facts(key="PS-NEW")]}
    result = _build_next_weekly_buffer(state, "2026-03-18", facts)
    assert "2026-03-18" in result
    assert "PS-NEW" in result["2026-03-18"]
    assert "PS-OLD" not in result["2026-03-18"]  # today's snapshot replaced


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


def test_run_agent_builds_weekly_buffer_in_next_memory():
    from unittest.mock import patch, MagicMock
    from agent import run_agent
    from models import AgentMemoryState
    from config import Settings

    settings = MagicMock(spec=Settings)
    settings.vertical_label_prefix = "vertical:"
    settings.label_to_vertical = {}
    settings.unchanged_stale_days = 5
    settings.jira_board_id = "PS"
    settings.jira_board_url = ""
    settings.max_items_per_vertical = 20
    settings.llm_webhook_url = None
    settings.roadmap_app_url = None
    settings.ps_agent_email = None

    from jira_client import JiraTicket
    ticket = JiraTicket(
        key="PS-1", summary="Test", status="To Do", status_category="new",
        assignee=None, reporter="ana", created="2026-03-18T10:00:00.000+0000",
        updated="2026-03-18T10:00:00.000+0000", last_status_change_at="2026-03-18T10:00:00.000+0000",
        description="", section="", criticality="", environment="", ticket_type="Bug",
        url="https://jira/PS-1", labels=["vertical:verification"],
    )
    memory = AgentMemoryState.empty()

    with patch("agent._build_next_weekly_buffer") as mock_buf:
        mock_buf.return_value = {"2026-03-18": {}}
        _, _, cpo_body, next_mem, _ = run_agent(
            settings=settings, tickets=[ticket], finalized_tickets=[],
            board_context=None, memory_state=memory, is_weekly_run=False,
        )

    assert cpo_body is None                   # daily run → no CPO
    mock_buf.assert_called_once()             # buffer helper always called
    assert next_mem.weekly_buffer == {"2026-03-18": {}}


def test_run_agent_returns_cpo_body_on_weekly_run():
    from unittest.mock import patch, MagicMock
    from agent import run_agent
    from models import AgentMemoryState

    from config import Settings
    settings = MagicMock(spec=Settings)
    settings.vertical_label_prefix = "vertical:"
    settings.label_to_vertical = {}
    settings.unchanged_stale_days = 5
    settings.jira_board_id = "PS"
    settings.jira_board_url = ""
    settings.max_items_per_vertical = 20
    settings.llm_webhook_url = None
    settings.roadmap_app_url = None
    settings.ps_agent_email = None

    from jira_client import JiraTicket
    ticket = JiraTicket(
        key="PS-1", summary="Test", status="To Do", status_category="new",
        assignee=None, reporter="ana", created="2026-03-18T10:00:00.000+0000",
        updated="2026-03-18T10:00:00.000+0000", last_status_change_at="2026-03-18T10:00:00.000+0000",
        description="", section="", criticality="", environment="", ticket_type="Bug",
        url="https://jira/PS-1", labels=["vertical:verification"],
    )
    memory = AgentMemoryState.empty()
    memory.weekly_buffer = {"2026-03-18": {"PS-1": WeeklyTicketSnapshot(
        status="To Do", status_category="new", days_without_status_change=1,
        is_stale=False, criticality=None, vertical="verification", reporter="ana",
        created="2026-03-18T10:00:00.000+0000", finalized_today=False,
    )}}

    with patch("agent._build_next_weekly_buffer") as mock_buf:
        mock_buf.return_value = memory.weekly_buffer
        _, _, cpo_body, next_mem, _ = run_agent(
            settings=settings, tickets=[ticket], finalized_tickets=[],
            board_context=None, memory_state=memory, is_weekly_run=True,
        )

    assert cpo_body is not None               # weekly run → CPO built
    assert "Reporte semanal" in cpo_body
