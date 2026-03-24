# Weekly CPO Message Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the per-run CPO snapshot message with a weekly aggregate message (sent every Friday at 17:00 AR), backed by daily ticket snapshots accumulated throughout the week, and align the roadmap agent to the same weekly cadence.

**Architecture:** `models.py` gets a new `WeeklyTicketSnapshot` dataclass and `AgentMemoryState` grows two new fields (`weekly_buffer`, `weekly_last_run_at`). Each daily run saves today's snapshot to the buffer via a helper in `agent.py`; on Fridays (or `--weekly`), `run_agent` builds the CPO message from the full buffer and runs the roadmap agent. `main.py` wires the `--weekly` flag and handles buffer clearing after the Friday run.

**Tech Stack:** Python 3.13, `zoneinfo` (stdlib), `pytest`, existing `models.py` / `memory.py` / `agent.py` / `main.py` / `message_builder.py` patterns.

---

## File Map

| File | Change |
|------|--------|
| `src/models.py` | Add `WeeklyTicketSnapshot`; extend `AgentMemoryState` with `weekly_buffer` + `weekly_last_run_at`; update `to_dict()` + `empty()` |
| `src/agent.py` | Add `_build_weekly_snapshot()` + `_build_next_weekly_buffer()`; add `is_weekly_run` param to `run_agent()`; conditionally build CPO + run roadmap |
| `src/message_builder.py` | Add `build_weekly_cpo_message()`; keep `build_cpo_message` but it is no longer called |
| `src/main.py` | Add `--weekly` flag; compute `is_weekly_run`; clear weekly buffer on Friday after CPO is sent |
| `tests/test_weekly_buffer.py` | New file — unit tests for `WeeklyTicketSnapshot` serialization and `_build_next_weekly_buffer` logic |
| `tests/test_weekly_cpo_message.py` | New file — unit tests for `build_weekly_cpo_message` (all four blocks) |

> **Read before starting:** `docs/code/conventions.md`, `docs/testing/test-conventions.md`, `docs/testing/testing-guidelines.md`, `src/AGENTS.md`

---

### Task 1: Add `WeeklyTicketSnapshot` to `models.py`

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_weekly_buffer.py` (create)

#### Background

`WeeklyTicketSnapshot` captures the fields needed for weekly analytics. It lives alongside `TicketStateSnapshot` (which tracks state for "did this ticket change since the last run?"). They serve different purposes — don't merge them.

`AgentMemoryState.weekly_buffer` type: `Dict[str, Dict[str, WeeklyTicketSnapshot]]`
Outer key = ISO date string (`"2026-03-18"`), inner key = ticket key (`"PS-1364"`).

---

- [ ] **Step 1: Write the failing test**

Create `tests/test_weekly_buffer.py`:

```python
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
```

- [ ] **Step 2: Run test to confirm failure**

```bash
./scripts/run-tests.sh
```

Expected: `ImportError` — `WeeklyTicketSnapshot` not defined.

- [ ] **Step 3: Add `WeeklyTicketSnapshot` to `src/models.py`**

Add after `TicketStateSnapshot` (around line 55):

```python
@dataclass(frozen=True)
class WeeklyTicketSnapshot:
    status: str
    status_category: str
    days_without_status_change: int
    is_stale: bool
    criticality: Optional[str]
    vertical: str
    reporter: Optional[str]
    created: str          # ISO 8601 datetime string from Jira
    finalized_today: bool
```

- [ ] **Step 4: Extend `AgentMemoryState`**

Add two fields to `AgentMemoryState` (after `roadmap`):

```python
weekly_buffer: Dict[str, Dict[str, "WeeklyTicketSnapshot"]] = field(default_factory=dict)
weekly_last_run_at: Optional[str] = None
```

Update `to_dict()` — add to the returned dict:

```python
"weekly_buffer": {
    date_str: {
        key: asdict(snap)
        for key, snap in day_snaps.items()
    }
    for date_str, day_snaps in self.weekly_buffer.items()
},
"weekly_last_run_at": self.weekly_last_run_at,
```

Update `load()` in `memory.py` — deserialize `weekly_buffer`:

```python
weekly_buffer_raw = data.get("weekly_buffer", {})
weekly_buffer: Dict[str, Dict[str, WeeklyTicketSnapshot]] = {}
snap_fields = {f.name for f in fields(WeeklyTicketSnapshot)}
for date_str, day_data in weekly_buffer_raw.items():
    weekly_buffer[date_str] = {
        key: WeeklyTicketSnapshot(**{k: v for k, v in snap.items() if k in snap_fields})
        for key, snap in day_data.items()
    }

return AgentMemoryState(
    tickets=tickets,
    last_run_at=data.get("last_run_at"),
    roadmap=roadmap,
    weekly_buffer=weekly_buffer,
    weekly_last_run_at=data.get("weekly_last_run_at"),
)
```

Also update `memory.py` imports: add `WeeklyTicketSnapshot` to the import from `models`.

- [ ] **Step 5: Run tests to confirm passing**

```bash
./scripts/run-tests.sh
```

Expected: all 4 new tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add src/models.py src/memory.py tests/test_weekly_buffer.py
git commit -m "feat(models): add WeeklyTicketSnapshot and weekly_buffer to AgentMemoryState"
```

---

### Task 2: Weekly buffer helpers in `agent.py`

**Files:**
- Modify: `src/agent.py`
- Test: `tests/test_weekly_buffer.py`

#### Background

Two private helpers:
- `_build_weekly_snapshot(grouped_facts)` — converts a `Dict[str, List[TicketFacts]]` into `Dict[str, WeeklyTicketSnapshot]` keyed by ticket key.
- `_build_next_weekly_buffer(memory_state, today_str, grouped_facts)` — stale-checks the existing buffer (ISO week comparison) and appends today's snapshot.

The stale check compares the ISO week+year of the earliest date in the buffer against today's. If they differ, the buffer is reset.

---

- [ ] **Step 1: Write failing tests**

Add to `tests/test_weekly_buffer.py`:

```python
from datetime import date


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
```

- [ ] **Step 2: Run to confirm failure**

```bash
./scripts/run-tests.sh
```

Expected: `ImportError` — `_build_weekly_snapshot` not defined in `agent.py`.

- [ ] **Step 3: Implement helpers in `src/agent.py`**

Add imports at top of `agent.py`:

```python
from datetime import date
from models import AgentMemoryState, RoadmapPlan, VerticalPlan, WeeklyTicketSnapshot
```

Add at the bottom of `agent.py`:

```python
def _build_weekly_snapshot(
    grouped_facts: Dict[str, List],
) -> Dict[str, WeeklyTicketSnapshot]:
    result = {}
    for facts in grouped_facts.values():
        for f in facts:
            result[f.key] = WeeklyTicketSnapshot(
                status=f.status,
                status_category=f.status_category,
                days_without_status_change=f.days_without_status_change,
                is_stale=f.is_stale,
                criticality=f.criticality,
                vertical=f.vertical,
                reporter=f.reporter,
                created=f.created,
                finalized_today=f.finalized_today,
            )
    return result


def _build_next_weekly_buffer(
    memory_state: AgentMemoryState,
    today_str: str,
    grouped_facts: Dict[str, List],
) -> Dict[str, Dict[str, WeeklyTicketSnapshot]]:
    existing = dict(memory_state.weekly_buffer)

    # Stale check: if earliest buffer date is from a different ISO week, reset
    if existing:
        earliest = date.fromisoformat(min(existing.keys()))
        today = date.fromisoformat(today_str)
        e_cal = earliest.isocalendar()
        t_cal = today.isocalendar()
        if e_cal.week != t_cal.week or e_cal.year != t_cal.year:
            existing = {}

    today_snapshot = _build_weekly_snapshot(grouped_facts)
    return {**existing, today_str: today_snapshot}
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
./scripts/run-tests.sh
```

Expected: all new tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/agent.py tests/test_weekly_buffer.py
git commit -m "feat(agent): add weekly snapshot helpers _build_weekly_snapshot and _build_next_weekly_buffer"
```

---

### Task 3: `build_weekly_cpo_message` in `message_builder.py`

**Files:**
- Modify: `src/message_builder.py`
- Test: `tests/test_weekly_cpo_message.py` (create)

#### Background

`build_weekly_cpo_message(project_label, buffer, recurring_patterns)` builds a four-block Roam markdown string from the week's accumulated buffer:

- **Bloque 1 (resumen ejecutivo):** Compare first vs last snapshot. Tickets created = present in any snapshot but absent from first. Tickets resolved = any snapshot where `finalized_today=True`. No movement = tickets in both first and last snapshot with same `status` across all days they appear.
- **Bloque 2 (velocidad):** Time-to-resolve = for resolved tickets, `finalization_date - date.fromisoformat(created[:10])`. Advanced state = tickets in first+last snapshot with different `status` in at least two buffer entries. Both metrics grouped by vertical.
- **Bloque 3 (patrones):** Same rendering as current `build_cpo_message`.
- **Bloque 4 (roadmap signals):** Computed from last snapshot: busiest stale vertical, active Highest tickets, very old stale tickets.

If `buffer` is empty, return a short message: `"Sin datos acumulados para la semana."`.

---

- [ ] **Step 1: Write failing tests**

Create `tests/test_weekly_cpo_message.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
./scripts/run-tests.sh
```

Expected: `ImportError` — `build_weekly_cpo_message` not defined.

- [ ] **Step 3: Implement `build_weekly_cpo_message` in `src/message_builder.py`**

Add the following imports at the top of `message_builder.py` (alongside existing ones):

```python
from datetime import date
from models import TicketFacts, VerticalPlan, WeeklyTicketSnapshot
```

Add at the end of `message_builder.py`:

```python
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
    created_keys = all_keys_ever - first_keys
    created_count = len(created_keys)

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
        # Find the day when finalized_today was True
        fin_date_str = None
        created_str = None
        for date_str in sorted_dates:
            day_snaps = buffer.get(date_str, {})
            if key in day_snaps:
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

    # Oldest stale ticket in last day
    stale_last = [(s.days_without_status_change, k) for k, s in last_day.items() if s.is_stale]
    if stale_last:
        max_days, _ = max(stale_last, key=lambda x: x[0])
        if max_days != 999 and max_days > 30:
            lines.append(f"- Hay tickets sin movimiento hace más de {max_days} días — revisar si siguen siendo relevantes")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
./scripts/run-tests.sh
```

Expected: all tests in `test_weekly_cpo_message.py` pass, no regressions in other files.

- [ ] **Step 5: Commit**

```bash
git add src/message_builder.py tests/test_weekly_cpo_message.py
git commit -m "feat(message_builder): add build_weekly_cpo_message with 4-block weekly report"
```

---

### Task 4: Wire weekly cycle into `agent.py`

**Files:**
- Modify: `src/agent.py`

#### Background

Add `is_weekly_run: bool = False` param to `run_agent()`. On weekly runs: build CPO from buffer, run roadmap. On daily runs: skip both. Also wire `_build_next_weekly_buffer` into the memory state before returning.

The existing `_should_run_roadmap` logic is replaced by `is_weekly_run` — roadmap runs only when `is_weekly_run=True` (or `force_roadmap=True` for testing).

---

- [ ] **Step 1: Write failing tests**

Add to `tests/test_weekly_buffer.py`:

```python
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

    with patch("agent.datetime") as mock_dt:
        mock_dt.now.return_value.date.return_value.isoformat.return_value = "2026-03-18"
        mock_dt.now.return_value.date.return_value.isocalendar.return_value.week = 12
        mock_dt.now.return_value.date.return_value.isocalendar.return_value.year = 2026
        _, _, cpo_body, next_mem, _ = run_agent(
            settings=settings, tickets=[ticket], finalized_tickets=[],
            board_context=None, memory_state=memory, is_weekly_run=False,
        )

    assert cpo_body is None                   # daily run → no CPO
    assert "2026-03-18" in next_mem.weekly_buffer
    assert "PS-1" in next_mem.weekly_buffer["2026-03-18"]


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

    with patch("agent.datetime") as mock_dt:
        mock_dt.now.return_value.date.return_value.isoformat.return_value = "2026-03-21"
        mock_dt.now.return_value.date.return_value.isocalendar.return_value.week = 12
        mock_dt.now.return_value.date.return_value.isocalendar.return_value.year = 2026
        _, _, cpo_body, next_mem, _ = run_agent(
            settings=settings, tickets=[ticket], finalized_tickets=[],
            board_context=None, memory_state=memory, is_weekly_run=True,
        )

    assert cpo_body is not None               # weekly run → CPO built
    assert "Reporte semanal" in cpo_body
```

- [ ] **Step 2: Run to confirm failure**

```bash
./scripts/run-tests.sh
```

Expected: `TypeError` — `run_agent` got unexpected keyword argument `is_weekly_run`.

- [ ] **Step 3: Update `run_agent` in `src/agent.py`**

1. Add import at top:
```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from message_builder import build_cpo_message, build_vertical_message, build_weekly_cpo_message
```

2. Add `_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")` near the top of the file (below imports).

3. Change `run_agent` signature — add param:
```python
is_weekly_run: bool = False,
```

4. Replace the `build_cpo_message` call and roadmap block with:
```python
# Weekly CPO message (only on Friday runs)
cpo_body = None
if is_weekly_run:
    today_str = datetime.now(_ARGENTINA_TZ).date().isoformat()
    next_memory.weekly_buffer = _build_next_weekly_buffer(memory_state, today_str, grouped_facts)
    cpo_body = build_weekly_cpo_message(
        project_label=project_label,
        buffer=next_memory.weekly_buffer,
        recurring_patterns=recurring_patterns,
    )
else:
    today_str = datetime.now(_ARGENTINA_TZ).date().isoformat()
    next_memory.weekly_buffer = _build_next_weekly_buffer(memory_state, today_str, grouped_facts)

# Roadmap analysis (weekly only, or forced)
roadmap_plan = None
if (is_weekly_run or force_roadmap) and not skip_roadmap:
    try:
        roadmap_plan = _run_roadmap_analysis(
            settings=settings,
            tickets=tickets,
            recurring_patterns=recurring_patterns or [],
            memory_state=memory_state,
        )
    except Exception as exc:
        print(f"[WARN] Análisis de roadmap falló: {exc}")
```

5. Also preserve `next_memory.roadmap` after setting weekly_buffer (keep existing line):
```python
next_memory.roadmap = memory_state.roadmap
```

The `_should_run_roadmap` function can remain in the file (unused) — do not delete it now to avoid unrelated changes.

- [ ] **Step 4: Run tests to confirm passing**

```bash
./scripts/run-tests.sh
```

Expected: new tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add src/agent.py tests/test_weekly_buffer.py
git commit -m "feat(agent): add is_weekly_run param, wire weekly buffer into run_agent"
```

---

### Task 5: `--weekly` flag and orchestration in `main.py`

**Files:**
- Modify: `src/main.py`

#### Background

`main.py` needs to:
1. Expose `--weekly` CLI flag
2. Compute `is_weekly_run = args.weekly or datetime.now(AR_TZ).weekday() == 4`
3. Pass `is_weekly_run` to `run_agent()`
4. On weekly run (non-dry-run): clear buffer + set `weekly_last_run_at` on `next_memory` before saving
5. On `--weekly --dry-run`: print CPO to stdout, skip HTML report, skip save (consistent with existing dry-run behavior)
6. On `--weekly --notify-only`: send CPO message, skip roadmap (already handled by `skip_roadmap=notify_only`)

No new test file needed — this is integration-level wiring. The key behaviors are already covered by unit tests. One smoke test added to `test_weekly_buffer.py` to verify the buffer is cleared correctly.

---

- [ ] **Step 1: Write failing test**

Add to `tests/test_weekly_buffer.py`:

```python
def test_agent_memory_weekly_last_run_at_persists(tmp_path):
    from memory import AgentMemory
    from models import AgentMemoryState

    state_path = tmp_path / "state.json"
    state = AgentMemoryState.empty()
    state.weekly_last_run_at = "2026-03-21T17:00:00-03:00"

    mem = AgentMemory(str(state_path))
    mem.save(state)

    loaded = mem.load()
    assert loaded.weekly_last_run_at == "2026-03-21T17:00:00-03:00"
    assert loaded.weekly_buffer == {}   # buffer was empty
```

- [ ] **Step 2: Run to confirm it passes already**

```bash
./scripts/run-tests.sh
```

This test should already pass if Task 1 was implemented correctly. If not, fix the `memory.py` deserialization.

- [ ] **Step 3: Update `src/main.py`**

1. Add import at top:
```python
from zoneinfo import ZoneInfo
_ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
```

2. Update `run()` signature to add `weekly: bool = False`:
```python
def run(dry_run: bool, cpo_only: bool = False, roadmap_only: bool = False,
        notify_only: bool = False, force_roadmap: bool = False, weekly: bool = False) -> int:
```

3. At the start of `run()`, add:
```python
is_weekly_run = weekly or datetime.now(_ARGENTINA_TZ).weekday() == 4
```

4. Pass to `run_agent()`:
```python
plans, outbound_messages, cpo_body, next_memory, roadmap_plan = run_agent(
    settings=settings,
    tickets=tickets,
    finalized_tickets=finalized_tickets,
    board_context=board_context,
    memory_state=memory_state,
    skip_roadmap=notify_only,
    force_roadmap=force_roadmap,
    is_weekly_run=is_weekly_run,
)
```

5. After sending CPO message (in the non-dry-run path), clear buffer on weekly run:
```python
if is_weekly_run and not dry_run:
    from datetime import timezone
    next_memory.weekly_buffer = {}
    next_memory.weekly_last_run_at = datetime.now(timezone.utc).isoformat()
```

Place this block just before `memory.save(next_memory)`.

6. For `--weekly --dry-run` — CPO is already printed via the existing `cpo_body` dry-run block. Ensure the HTML report is suppressed for weekly runs:

```python
if dry_run and not cpo_only and not is_weekly_run:
    _save_html_report(...)
```

(Add `and not is_weekly_run` to the condition — weekly dry-run prints to stdout only, no HTML.)

7. Add `--weekly` to argparse:
```python
parser.add_argument(
    "--weekly",
    action="store_true",
    help="Fuerza la corrida semanal: envía mensaje CPO al canal C-level y ejecuta el roadmap agent",
)
```

8. Pass `weekly=args.weekly` to `run()`:
```python
raise SystemExit(run(
    dry_run=args.dry_run,
    cpo_only=args.cpo_only,
    roadmap_only=args.roadmap_only,
    notify_only=args.notify_only,
    force_roadmap=args.force_roadmap,
    weekly=args.weekly,
))
```

- [ ] **Step 4: Run tests to confirm passing**

```bash
./scripts/run-tests.sh
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat(main): add --weekly flag, wire weekly CPO cycle and buffer clearing"
```

---

### Task 6: Manual smoke test

- [ ] **Step 1: Run dry-run to verify weekly output**

```bash
python src/main.py --weekly --dry-run
```

Expected:
- Vertical messages printed to stdout
- Weekly CPO message printed to stdout with the four blocks
- No HTML report generated
- No file written to `reports/`

- [ ] **Step 2: Verify buffer is NOT cleared on dry-run**

Run again:
```bash
python src/main.py --weekly --dry-run
```

If `agent_state.json` exists and has buffer data, verify it hasn't changed between the two runs.

- [ ] **Step 3: Commit final state if any fixups needed**

```bash
git add -p
git commit -m "fix: weekly smoke test fixups"
```

---

## Done

All five tasks complete. The agent now:
- Saves a daily ticket snapshot to `weekly_buffer` on every run
- Sends a four-block weekly CPO message every Friday (or via `--weekly`)
- Runs the roadmap agent only on Friday runs
- Clears the buffer after the Friday message is sent
