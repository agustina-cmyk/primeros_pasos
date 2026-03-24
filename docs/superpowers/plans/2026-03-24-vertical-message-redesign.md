# Vertical Message Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el modelo evento-driven de mensajes verticales por un reporte de estado completo del tablero, con tres secciones: cambios, sin movimiento <5d, y sin movimiento ≥5d.

**Architecture:** Se modifican las capas de datos (`models.py`), clasificación (`classifier.py`), planeamiento (`planner.py`) y renderizado (`message_builder.py`) de forma secuencial y con TDD. Cada capa depende de la anterior, por lo que las tareas deben ejecutarse en orden.

**Tech Stack:** Python 3.11+, pytest, dataclasses, zoneinfo (Argentina TZ). Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-03-24-vertical-message-redesign.md`

---

## File Map

| Archivo | Rol | Cambio |
|---|---|---|
| `src/models.py` | Contrato de datos de TicketFacts | Eliminar `status_changed_today`; agregar `days_without_status_change: int` |
| `src/config.py` | Settings del agente | Renombrar `stale_ticket_days` → `unchanged_stale_days`; agregar `jira_board_url: str` |
| `src/classifier.py` | Clasificación de tickets desde Jira | Calcular `days_without_status_change` con fallback y sentinel; usar nuevo umbral |
| `src/planner.py` | Construcción del plan de acciones por vertical | 5 action types → 3: `notify_changes`, `notify_unchanged_recent`, `notify_unchanged_stale` |
| `src/message_builder.py` | Renderizado del cuerpo del mensaje | Nuevo título + 3 secciones + link al board cuando hay cap |
| `src/agent.py` | Orquestación del agente | Actualizar 2 call sites de `stale_ticket_days` y agregar `board_url` a `build_vertical_message` |
| `.env` | Variables de entorno | Renombrar `STALE_TICKET_DAYS` → `UNCHANGED_STALE_DAYS`; agregar `JIRA_BOARD_URL` (vacío) |
| `tests/test_classifier.py` | Tests del clasificador | Nuevo archivo |
| `tests/test_planner.py` | Tests del planner | Nuevo archivo |
| `tests/test_message_builder.py` | Tests del message builder | Nuevo archivo |

---

## Task 1: Foundation — models, config, agent, .env

**Files:**
- Modify: `src/models.py`
- Modify: `src/config.py`
- Modify: `src/agent.py`
- Modify: `.env`

> Esta tarea modifica contratos de datos y configuración. Los tests existentes se deben seguir pasando al finalizar.

- [ ] **Step 1: Actualizar `TicketFacts` en `models.py`**

  Eliminar el campo `status_changed_today: bool` (línea 26) y agregar `days_without_status_change: int` después de `is_stale`. El modelo queda:

  ```python
  @dataclass(frozen=True)
  class TicketFacts:
      key: str
      vertical: str
      summary: str
      status: str
      status_category: str
      assignee: Optional[str]
      reporter: Optional[str]
      created: str
      updated: str
      last_status_change_at: str
      description: str
      section: str
      criticality: str
      environment: str
      ticket_type: str
      url: str
      labels: List[str]
      created_today: bool
      finalized_today: bool
      is_stale: bool
      days_without_status_change: int
      changed_since_last_run: bool
      status_changed: bool
      assignee_changed: bool
  ```

- [ ] **Step 2: Actualizar `config.py`**

  En el dataclass `Settings`, renombrar `stale_ticket_days: int` → `unchanged_stale_days: int` y agregar `jira_board_url: str = ""`.

  En `load_settings()`, reemplazar:
  ```python
  stale_ticket_days=int(os.getenv("STALE_TICKET_DAYS", "15")),
  ```
  Por:
  ```python
  unchanged_stale_days=int(os.getenv("UNCHANGED_STALE_DAYS", "5")),
  jira_board_url=os.getenv("JIRA_BOARD_URL", "").strip(),
  ```

- [ ] **Step 3: Actualizar call sites en `agent.py`**

  Hay tres cambios en `agent.py`:

  **a)** Línea 25 — en la llamada `classify_tickets` dentro de `run_agent`:
  ```python
  # Antes:
  stale_ticket_days=settings.stale_ticket_days,
  # Después:
  unchanged_stale_days=settings.unchanged_stale_days,
  ```

  **b)** Líneas 38-44 — agregar `board_url` y quitar el parámetro `channel_url` en la llamada a `build_vertical_message`:
  ```python
  title, body = build_vertical_message(
      project_label=project_label,
      plan=plan,
      board_url=settings.jira_board_url,
      max_items=settings.max_items_per_vertical,
      last_run_at=memory_state.last_run_at,
  )
  ```

  **c)** Línea 97 — en la llamada `classify_tickets` dentro de `_should_run_roadmap`:
  ```python
  # Antes:
  stale_ticket_days=settings.stale_ticket_days,
  # Después:
  unchanged_stale_days=settings.unchanged_stale_days,
  ```

- [ ] **Step 4: Actualizar `.env`**

  Reemplazar `STALE_TICKET_DAYS=15` por:
  ```
  UNCHANGED_STALE_DAYS=5
  JIRA_BOARD_URL=
  ```

- [ ] **Step 5: Verificar que los tests existentes pasan**

  Los cambios de modelo romperán `classifier.py` temporalmente (usa `status_changed_today=` como keyword arg en el `TicketFacts` constructor). Actualizar temporalmente esa línea en `classifier.py` para compilar — en el Task 2 se reemplazará completamente.

  En `classifier.py`, reemplazar las líneas que construyen `TicketFacts` con `status_changed_today=...`:
  ```python
  # Eliminar esta línea del constructor de TicketFacts en classify_tickets:
  status_changed_today=_is_same_local_day(last_status_change_dt, now_local),
  # Agregar en su lugar (placeholder hasta Task 2):
  days_without_status_change=0,
  ```

  También actualizar la firma de `classify_tickets` para renombrar el parámetro:
  ```python
  def classify_tickets(
      tickets: List[JiraTicket],
      memory_state: AgentMemoryState,
      label_prefix: str,
      label_to_vertical: Dict[str, str],
      unchanged_stale_days: int,   # renombrado desde stale_ticket_days
  ) -> Dict[str, List[TicketFacts]]:
  ```
  Y actualizar la variable interna:
  ```python
  stale_cutoff = now_local - timedelta(days=unchanged_stale_days)
  ```

  Correr los tests:
  ```
  ./scripts/run-tests.sh
  ```
  Esperado: todos los tests existentes pasan (los tests actuales no cubren classifier/planner).

- [ ] **Step 6: Commit**

  ```bash
  git add src/models.py src/config.py src/agent.py src/classifier.py .env
  git commit -m "refactor: foundation for vertical message redesign — models, config, agent"
  ```

---

## Task 2: Classifier — calcular `days_without_status_change`

**Files:**
- Create: `tests/test_classifier.py`
- Modify: `src/classifier.py`

- [ ] **Step 1: Escribir los tests**

  Crear `tests/test_classifier.py`:

  ```python
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
  ```

- [ ] **Step 2: Correr los tests y verificar que fallan**

  ```
  ./scripts/run-tests.sh tests/test_classifier.py -v
  ```
  Esperado: varios FAIL — `days_without_status_change` es `0` hardcodeado, `is_stale` usa lógica vieja.

- [ ] **Step 3: Implementar `days_without_status_change` en `classifier.py`**

  Reemplazar el bloque `facts = TicketFacts(...)` dentro de `classify_tickets` para calcular el nuevo campo y actualizar `is_stale`:

  ```python
  days = _compute_days_without_status_change(
      last_status_change_at=ticket.last_status_change_at,
      created=ticket.created,
      now=now_local,
  )

  facts = TicketFacts(
      key=ticket.key,
      vertical=vertical,
      summary=ticket.summary,
      status=ticket.status,
      status_category=ticket.status_category,
      assignee=ticket.assignee,
      reporter=ticket.reporter,
      created=ticket.created,
      updated=ticket.updated,
      last_status_change_at=ticket.last_status_change_at,
      description=ticket.description,
      section=ticket.section,
      criticality=ticket.criticality,
      environment=ticket.environment,
      ticket_type=ticket.ticket_type,
      url=ticket.url,
      labels=ticket.labels,
      created_today=_is_same_local_day(created_dt, now_local),
      finalized_today=ticket.status_category.lower() == "done" and _is_same_local_day(last_status_change_dt, now_local),
      is_stale=days >= unchanged_stale_days,
      days_without_status_change=days,
      changed_since_last_run=_changed_since_last_run(ticket, previous),
      status_changed=bool(previous and previous.status != ticket.status),
      assignee_changed=bool(previous and previous.assignee != ticket.assignee),
  )
  ```

  Agregar la función helper al final del archivo (antes de `_changed_since_last_run`):

  ```python
  def _compute_days_without_status_change(
      last_status_change_at: str,
      created: str,
      now: datetime,
  ) -> int:
      anchor = _safe_parse_jira_datetime(last_status_change_at)
      if anchor is None:
          anchor = _safe_parse_jira_datetime(created)
      if anchor is None:
          return 999
      return (now.date() - anchor.astimezone(now.tzinfo).date()).days
  ```

  También eliminar la variable `stale_cutoff` (ya no se usa):
  ```python
  # Eliminar esta línea:
  stale_cutoff = now_local - timedelta(days=unchanged_stale_days)
  # Y la línea que la usaba en TicketFacts:
  is_stale=bool(last_status_change_dt and last_status_change_dt.astimezone() <= stale_cutoff),
  ```

- [ ] **Step 4: Correr los tests y verificar que pasan**

  ```
  ./scripts/run-tests.sh tests/test_classifier.py -v
  ```
  Esperado: 7/7 PASS.

- [ ] **Step 5: Correr todos los tests**

  ```
  ./scripts/run-tests.sh
  ```
  Esperado: todos pasan.

- [ ] **Step 6: Commit**

  ```bash
  git add src/classifier.py tests/test_classifier.py
  git commit -m "feat(classifier): agregar days_without_status_change con fallback y sentinel"
  ```

---

## Task 3: Planner — nuevos action types

**Files:**
- Create: `tests/test_planner.py`
- Modify: `src/planner.py`

- [ ] **Step 1: Escribir los tests**

  Crear `tests/test_planner.py`:

  ```python
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
      ticket = _make_facts(created_today=True, days_without_status_change=0)
      plan = build_vertical_plan("verification", [ticket])
      types = [a.action_type for a in plan.actions]
      assert "notify_changes" in types


  def test_finalized_today_goes_to_notify_changes():
      ticket = _make_facts(
          finalized_today=True,
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
      ticket = _make_facts(status_category="done", finalized_today=False)
      plan = build_vertical_plan("verification", [ticket])
      all_tickets = [t for a in plan.actions for t in a.tickets]
      assert ticket not in all_tickets


  def test_finalized_today_done_ticket_is_included():
      ticket = _make_facts(
          status_category="done",
          finalized_today=True,
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
      ticket = _make_facts(created_today=True, days_without_status_change=0)
      plan = build_vertical_plan("verification", [ticket])
      old_types = {"notify_created_today", "notify_finished_today", "notify_status_changed", "notify_stale_tickets"}
      emitted = {a.action_type for a in plan.actions}
      assert emitted.isdisjoint(old_types)
  ```

- [ ] **Step 2: Correr los tests y verificar que fallan**

  ```
  ./scripts/run-tests.sh tests/test_planner.py -v
  ```
  Esperado: múltiples FAIL — planner todavía emite action types viejos.

- [ ] **Step 3: Implementar el nuevo planner**

  Reemplazar el contenido de `src/planner.py` completo:

  ```python
  from typing import List

  from models import AgentAction, TicketFacts, VerticalPlan


  def build_vertical_plan(vertical: str, tickets: List[TicketFacts]) -> VerticalPlan:
      actions: List[AgentAction] = []

      # Excluir tickets done que no finalizaron hoy
      active = [t for t in tickets if t.status_category.lower() != "done" or t.finalized_today]

      # Bucket 1: cambios (status_changed, created_today, finalized_today)
      changes = [
          t for t in active
          if t.status_changed or t.created_today or t.finalized_today
      ]
      changes_keys = {t.key for t in changes}

      # Buckets de sin movimiento (solo tickets que no están en changes)
      unchanged = [t for t in active if t.key not in changes_keys]
      recent = [t for t in unchanged if not t.is_stale]
      stale = [t for t in unchanged if t.is_stale]

      if changes:
          actions.append(AgentAction(
              action_type="notify_changes",
              vertical=vertical,
              reason="Tickets con cambios desde la última corrida.",
              tickets=_sort_changes(changes),
          ))

      if recent:
          actions.append(AgentAction(
              action_type="notify_unchanged_recent",
              vertical=vertical,
              reason="Tickets activos sin cambio de estado en menos de 5 días.",
              tickets=_sort_recent(recent),
          ))

      if stale:
          actions.append(AgentAction(
              action_type="notify_unchanged_stale",
              vertical=vertical,
              reason="Tickets activos sin cambio de estado en 5 días o más.",
              tickets=_sort_stale(stale),
          ))

      return VerticalPlan(vertical=vertical, actions=actions)


  def _sort_changes(tickets: List[TicketFacts]) -> List[TicketFacts]:
      return sorted(tickets, key=lambda t: t.updated, reverse=True)


  def _sort_recent(tickets: List[TicketFacts]) -> List[TicketFacts]:
      return sorted(tickets, key=lambda t: t.days_without_status_change)


  def _sort_stale(tickets: List[TicketFacts]) -> List[TicketFacts]:
      return sorted(
          tickets,
          key=lambda t: (
              0 if (t.criticality or "").lower() == "highest" else 1,
              -t.days_without_status_change,
          ),
      )
  ```

- [ ] **Step 4: Correr los tests y verificar que pasan**

  ```
  ./scripts/run-tests.sh tests/test_planner.py -v
  ```
  Esperado: 12/12 PASS.

- [ ] **Step 5: Correr todos los tests**

  ```
  ./scripts/run-tests.sh
  ```
  Esperado: todos pasan.

- [ ] **Step 6: Commit**

  ```bash
  git add src/planner.py tests/test_planner.py
  git commit -m "feat(planner): reemplazar 5 action types por notify_changes/unchanged_recent/unchanged_stale"
  ```

---

## Task 4: Message Builder — nuevo formato

**Files:**
- Create: `tests/test_message_builder.py`
- Modify: `src/message_builder.py`

- [ ] **Step 1: Escribir los tests**

  Crear `tests/test_message_builder.py`:

  ```python
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
          is_stale=False,
          days_without_status_change=3,
          changed_since_last_run=False,
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
      assert "In Progress: 1" in title
      assert "Vertical: verification" in title


  def test_title_no_done_tickets():
      done = _make_facts(status="Done", status_category="done", finalized_today=False)
      plan = _make_plan(actions=[_make_action("notify_unchanged_recent", [done])])
      title, _ = build_vertical_message("PS", plan, board_url="", max_items=20)
      assert "Done" not in title


  def test_title_no_active_tickets_shows_fallback():
      plan = _make_plan(actions=[])
      title, _ = build_vertical_message("PS", plan, board_url="", max_items=20)
      assert "Sin tickets activos" in title


  # --- Sección cambios ---

  def test_changes_section_header_present():
      ticket = _make_facts(status_changed=True)
      plan = _make_plan(actions=[_make_action("notify_changes", [ticket])])
      _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
      assert "🔄" in body
      assert "Cambios desde" in body


  def test_changes_section_shows_new_tag_for_created_today():
      ticket = _make_facts(created_today=True)
      plan = _make_plan(actions=[_make_action("notify_changes", [ticket])])
      _, body = build_vertical_message("PS", plan, board_url="", max_items=20)
      assert "🆕" in body


  def test_changes_section_shows_finalized_tag_and_reporter_mention():
      ticket = _make_facts(finalized_today=True, status_category="done", reporter="agus")
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
  ```

- [ ] **Step 2: Correr los tests y verificar que fallan**

  ```
  ./scripts/run-tests.sh tests/test_message_builder.py -v
  ```
  Esperado: múltiples FAIL — el message builder usa el formato viejo y la firma tiene `channel_url`.

- [ ] **Step 3: Implementar el nuevo message builder**

  Reemplazar el contenido completo de `src/message_builder.py`:

  ```python
  from collections import Counter
  from datetime import datetime, timezone
  from typing import Dict, List, Optional, Tuple

  from models import TicketFacts, VerticalPlan


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
      tags = _tags(t, include_days=False)
      reporter = f"@{t.reporter}" if t.reporter else "sin informador"
      return f"- [{t.key}]({t.url}) {tags}— {t.summary}\n  {t.status} | {reporter}"


  def _ticket_line_unchanged(t: TicketFacts) -> str:
      tags = _tags(t, include_days=False)
      days_label = "–" if t.days_without_status_change == 999 else f"{t.days_without_status_change}d"
      reporter = f"@{t.reporter}" if t.reporter else "sin informador"
      return f"- [{t.key}]({t.url}) {tags}— {t.summary}\n  {t.status} · {days_label} | {reporter}"


  def _tags(t: TicketFacts, include_days: bool = False) -> str:
      parts = []
      if t.created_today:
          parts.append("🆕")
      if t.finalized_today:
          parts.append("✅")
      if (t.criticality or "").lower() == "highest":
          parts.append("🚨")
      return (" ".join(parts) + " ") if parts else ""


  def _unique_reporters(tickets: List[TicketFacts]) -> List[str]:
      seen: List[str] = []
      for t in tickets:
          if t.reporter and t.reporter not in seen:
              seen.append(t.reporter)
      return seen


  def build_cpo_message(
      project_label: str,
      grouped_facts: Dict[str, List[TicketFacts]],
      recurring_patterns=None,
  ) -> str:
      from datetime import date as date_type

      all_tickets = [t for tickets in grouped_facts.values() for t in tickets]
      active = [t for t in all_tickets if t.status_category.lower() != "done"]
      stale = [t for t in active if t.is_stale]
      highest = [t for t in active if (t.criticality or "").lower() == "highest"]
      created_today = [t for t in all_tickets if t.created_today]
      finalized_today = [t for t in all_tickets if t.finalized_today]

      today = datetime.now(timezone.utc).date()
      lines: List[str] = []

      lines.append(f"📊 **Análisis del tablero — {project_label}**")
      lines.append("")
      lines.append(
          f"Total activos: **{len(active)}** | Estancados: **{len(stale)}** | "
          f"Críticos (Highest): **{len(highest)}** | Creados hoy: **{len(created_today)}** | Finalizados hoy: **{len(finalized_today)}**"
      )
      lines.append("")

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

      stale_with_age = []
      for t in stale:
          stale_with_age.append((t.days_without_status_change, t))
      stale_with_age.sort(key=lambda x: x[0], reverse=True)

      lines.append("**⏳ Tickets sin movimiento más prolongado**")
      for days, t in stale_with_age[:8]:
          age_label = "–" if days == 999 else f"{days}d"
          alert = " 🚨" if (t.criticality or "").lower() == "highest" else ""
          lines.append(f"- [{t.key}]({t.url}) ({t.vertical}) — {age_label} · {t.summary}{alert}")
      lines.append("")

      if recurring_patterns:
          lines.append("**🔁 Patrones recurrentes**")
          for p in recurring_patterns:
              keys_str = ", ".join(p.ticket_keys)
              lines.append(f"- **{p.label}** ({p.count} tickets: {keys_str})")
              lines.append(f"  → _{p.recommendation}_")
          lines.append("")

      status_count: Dict[str, int] = {}
      for t in active:
          status_count[t.status] = status_count.get(t.status, 0) + 1
      lines.append("**Distribución por estado**")
      for status, count in sorted(status_count.items(), key=lambda x: -x[1]):
          lines.append(f"- {status}: {count}")
      lines.append("")

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
  ```

- [ ] **Step 4: Correr los tests del message builder y verificar que pasan**

  ```
  ./scripts/run-tests.sh tests/test_message_builder.py -v
  ```
  Esperado: todos PASS.

- [ ] **Step 5: Correr todos los tests**

  ```
  ./scripts/run-tests.sh
  ```
  Esperado: todos pasan.

- [ ] **Step 6: Verificar el output con dry-run real**

  ```
  python3 src/main.py --dry-run 2>&1 | head -80
  ```
  Verificar que el mensaje de `verification` tiene las 3 secciones (`🔄`, `📋`, `⏳`) y que PS-1364 aparece en "Sin movimiento — menos de 5 días".

- [ ] **Step 7: Commit**

  ```bash
  git add src/message_builder.py tests/test_message_builder.py
  git commit -m "feat(message_builder): nuevo formato con cambios / sin movimiento <5d / ≥5d"
  ```

---

## Verificación final

- [ ] Correr la suite completa:

  ```
  ./scripts/run-tests.sh
  ```
  Esperado: todos los tests pasan (16 existentes + ~26 nuevos).

- [ ] Correr dry-run y confirmar el formato:

  ```
  python3 src/main.py --dry-run 2>&1
  ```
  Verificar:
  - Títulos muestran distribución de estados (ej: `Tareas por hacer: 18 · DEV IN PROGRESS: 2`)
  - Sección `🔄 Cambios` con tags 🆕/✅ correctos
  - Sección `📋 Sin movimiento — menos de 5 días` con días
  - Sección `⏳ Sin movimiento — más de 5 días` con críticos primero
  - PS-1364 visible en verificación bajo la sección de <5 días

- [ ] Limpiar el archivo prototipo (ya no necesario):

  ```bash
  git rm scripts/preview_new_format.py
  git commit -m "chore: eliminar script de prototipo preview_new_format.py"
  ```
