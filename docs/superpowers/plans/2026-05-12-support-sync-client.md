# Support Sync Client — Plan B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el agente Python pushee los tickets clasificados al endpoint `POST /api/support-tickets/sync` de la roadmap-app en cada corrida de `--roadmap-only`, populando la tabla `SupportTicket` que ya existe en producción.

**Architecture:** Un módulo nuevo `src/roadmap_support_client.py` (paralelo a `src/roadmap_client.py`) que serializa `TicketFacts` al payload del endpoint y hace el POST. Se invoca desde `src/main.py` después de `run_agent` (que ya hace la clasificación). Best-effort: si la sincro falla, el resto del agente sigue ejecutándose (notificaciones a Roam, análisis CPO, etc.).

**Tech Stack:** Python 3.13, `requests`, `pytest`, `unittest.mock`. Sin nuevas dependencias.

**Spec base:** `/Users/agusalvarez/Projects/roadmap-app/docs/superpowers/specs/2026-05-05-support-metrics-design.md` (Phase 3: Sincronización agente → roadmap-app).

**Plan A reference:** Tasks 1-14 ya mergeados a `main` en roadmap-app. Endpoint `POST /api/support-tickets/sync` en producción.

**Test command:** `./scripts/run-tests.sh` (pytest via venv).

---

## File Map

- **Create** `src/roadmap_support_client.py` — `sync_support_tickets(app_url, token, facts) -> SyncResult` + dataclass `SyncResult`.
- **Create** `tests/test_roadmap_support_client.py` — unit tests mockeando `requests.post`.
- **Modify** `src/agent.py` — `run_agent` agrega `grouped_facts` (o lista plana de facts) al tuple de retorno, así `main.py` puede sincronizarlos sin re-clasificar.
- **Modify** `src/main.py` — después de `run_agent`, si NO es `notify_only`, login + sync (best-effort, try/except).
- **Modify (opcional)** `docs/configuration/environment-variables.md` — no se agregan vars nuevas; las existentes (ROADMAP_APP_URL, supabase URL/anon_key, PS_AGENT_EMAIL/PASSWORD) ya cubren auth.

---

## Task 1: Crear `src/roadmap_support_client.py`

**Files:**
- Create: `src/roadmap_support_client.py`

**Step 1: Escribir el módulo**

```python
"""Cliente HTTP para sincronizar tickets de soporte a la roadmap-app.

Endpoint: POST {app_url}/api/support-tickets/sync
Auth: Bearer token (Supabase access token, mismo patrón que roadmap_client.py)
"""

from dataclasses import dataclass
from typing import List, Dict, Any

import requests

from models import TicketFacts


@dataclass(frozen=True)
class SyncResult:
    synced: int
    errors: List[Dict[str, str]]  # cada item: { "key": str, "message": str }


def _ticket_to_payload(facts: TicketFacts) -> Dict[str, Any]:
    """Convierte un TicketFacts al shape esperado por el endpoint."""
    resolved_at = facts.last_status_change_at if facts.status_category == "Done" else None
    return {
        "key":         facts.key,
        "createdAt":   facts.created,
        "resolvedAt":  resolved_at,
        "status":      facts.status,
        "vertical":    facts.vertical,
        "criticality": facts.criticality or None,
        "url":         facts.url,
    }


def sync_support_tickets(
    app_url: str,
    token: str,
    facts: List[TicketFacts],
    timeout: int = 30,
) -> SyncResult:
    """Pushea los tickets clasificados al endpoint /api/support-tickets/sync.

    Idempotente: el endpoint hace upsert por key. Backfill automático en la
    primera corrida (cualquier ticket que el agente vea en el board se sincroniza).
    """
    payload = {"tickets": [_ticket_to_payload(f) for f in facts]}
    response = requests.post(
        f"{app_url.rstrip('/')}/api/support-tickets/sync",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return SyncResult(
        synced=int(data.get("synced", 0)),
        errors=list(data.get("errors", [])),
    )
```

**Step 2: Verify file**

```bash
pwd  # /Users/agusalvarez/Documents/Proyectos Vaas/.worktrees/feat-support-sync (o equivalente)
git rev-parse --abbrev-ref HEAD  # feat/support-sync-client
ls src/roadmap_support_client.py  # exists
python -c "from src.roadmap_support_client import sync_support_tickets, SyncResult"  # imports OK (requires PYTHONPATH=src)
```

Si el import directo no funciona, probá `cd src && python -c "from roadmap_support_client import sync_support_tickets, SyncResult"`. El proyecto usa imports planos desde `src/` (ver patrón en `roadmap_client.py` que hace `from models import ...` sin prefix `src.`).

**Step 3: Commit**

```bash
git rev-parse --abbrev-ref HEAD  # MUST be feat/support-sync-client
git add src/roadmap_support_client.py
git commit -m "feat(support-sync): add roadmap-app sync client"
```

---

## Task 2: Tests para `roadmap_support_client`

**Files:**
- Create: `tests/test_roadmap_support_client.py`

**Step 1: Escribir tests siguiendo el patrón de `tests/test_roadmap_client.py`**

```python
import pytest
from unittest.mock import MagicMock, patch

from models import TicketFacts


def _make_facts(**overrides) -> TicketFacts:
    """Helper para construir TicketFacts con defaults razonables."""
    defaults = dict(
        key="PS-1",
        vertical="payments",
        summary="Test",
        status="In Progress",
        status_category="In Progress",
        assignee=None,
        reporter=None,
        created="2026-04-15T10:00:00.000+0000",
        updated="2026-04-15T10:00:00.000+0000",
        last_status_change_at="2026-04-15T10:00:00.000+0000",
        description="",
        section="",
        criticality="High",
        environment="",
        ticket_type="Bug",
        url="https://example.atlassian.net/browse/PS-1",
        labels=[],
        created_today=False,
        finalized_today=False,
        created_since_last_message=False,
        finalized_since_last_message=False,
        is_stale=False,
        days_without_status_change=0,
        status_changed=False,
        assignee_changed=False,
    )
    defaults.update(overrides)
    return TicketFacts(**defaults)


@pytest.fixture
def mock_sync_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"synced": 2, "errors": []}
    mock.raise_for_status = MagicMock()
    return mock


def test_sync_with_tickets_returns_synced_count(mock_sync_response):
    facts = [_make_facts(key="PS-1"), _make_facts(key="PS-2", vertical="core")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        result = roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    assert result.synced == 2
    assert result.errors == []
    # Verify payload shape
    args, kwargs = mock_post.call_args
    assert args[0] == "https://app.vercel.app/api/support-tickets/sync"
    assert kwargs["headers"]["Authorization"] == "Bearer test-jwt"
    payload = kwargs["json"]
    assert len(payload["tickets"]) == 2
    assert payload["tickets"][0]["key"] == "PS-1"
    assert payload["tickets"][0]["vertical"] == "payments"


def test_resolved_ticket_includes_resolvedAt(mock_sync_response):
    facts = [_make_facts(
        key="PS-CLOSED",
        status="Done",
        status_category="Done",
        last_status_change_at="2026-04-20T15:00:00.000+0000",
    )]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["resolvedAt"] == "2026-04-20T15:00:00.000+0000"


def test_open_ticket_has_null_resolvedAt(mock_sync_response):
    facts = [_make_facts(status_category="In Progress")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["resolvedAt"] is None


def test_empty_criticality_serializes_as_null(mock_sync_response):
    facts = [_make_facts(criticality="")]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["tickets"][0]["criticality"] is None


def test_url_normalized_trailing_slash(mock_sync_response):
    facts = [_make_facts()]
    with patch("roadmap_support_client.requests.post", return_value=mock_sync_response) as mock_post:
        import roadmap_support_client
        roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app/",  # trailing slash
            token="test-jwt",
            facts=facts,
        )
    assert mock_post.call_args.args[0] == "https://app.vercel.app/api/support-tickets/sync"


def test_partial_errors_returned_in_result():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"synced": 1, "errors": [{"key": "PS-2", "message": "DB busy"}]}
    mock.raise_for_status = MagicMock()
    facts = [_make_facts(key="PS-1"), _make_facts(key="PS-2")]
    with patch("roadmap_support_client.requests.post", return_value=mock):
        import roadmap_support_client
        result = roadmap_support_client.sync_support_tickets(
            app_url="https://app.vercel.app",
            token="test-jwt",
            facts=facts,
        )
    assert result.synced == 1
    assert len(result.errors) == 1
    assert result.errors[0]["key"] == "PS-2"


def test_raise_for_status_propagates_http_errors():
    mock = MagicMock()
    mock.raise_for_status.side_effect = Exception("401 Unauthorized")
    with patch("roadmap_support_client.requests.post", return_value=mock):
        import roadmap_support_client
        with pytest.raises(Exception, match="401"):
            roadmap_support_client.sync_support_tickets(
                app_url="https://app.vercel.app",
                token="bad",
                facts=[_make_facts()],
            )
```

**Step 2: Run tests**

```bash
./scripts/run-tests.sh tests/test_roadmap_support_client.py
# Expected: 7 tests pass
```

**Step 3: Verify branch + commit**

```bash
git rev-parse --abbrev-ref HEAD  # MUST be feat/support-sync-client
git add tests/test_roadmap_support_client.py
git commit -m "test(support-sync): unit tests for roadmap support client"
```

---

## Task 3: Integrar en `src/agent.py` y `src/main.py`

**Files:**
- Modify: `src/agent.py` — exponer `grouped_facts` desde `run_agent`
- Modify: `src/main.py` — login + sync best-effort después de `run_agent`

**Step 1: Modificar `src/agent.py` para retornar los facts clasificados**

Buscar la signatura actual:
```python
def run_agent(
    ...
) -> Tuple[Dict[str, VerticalPlan], List[Tuple[str, str, str]], str, AgentMemoryState, Optional[RoadmapPlan]]:
```

(Si la signatura no es exactamente esa, adaptar.)

Cambiar el return statement final de `run_agent` para incluir `grouped_facts` (un `Dict[str, List[TicketFacts]]`). El `grouped_facts` ya se calcula al principio de la función — solo agregamos al return.

Pseudo-código:
```python
return plans, outbound_messages, cpo_body, next_memory, roadmap_plan, grouped_facts
```

Y actualizar el type hint del return correspondientemente. Si tipa con `Tuple[...]`, agregar `Dict[str, List[TicketFacts]]` al final.

**Step 2: Modificar `src/main.py` para usar el nuevo retorno y llamar al sync**

A. En el call site de `run_agent` (línea ~59 del archivo actual), agregar `grouped_facts` al unpack:

```python
plans, outbound_messages, cpo_body, next_memory, roadmap_plan, grouped_facts = run_agent(
    ...
)
```

B. Después de ese call (alrededor de línea 68, antes del bloque "if not outbound_messages..."), agregar la sincronización best-effort. Solo correr si `not notify_only` (los flows `--notify-only` no tienen por qué sincronizar):

```python
if not notify_only:
    _sync_support_tickets(settings, grouped_facts)
```

C. Agregar la función helper al final del archivo (después de `_notify_cpo_roadmap`):

```python
def _sync_support_tickets(settings, grouped_facts) -> None:
    """Pushea los tickets clasificados a la roadmap-app. Best-effort.

    No interrumpe el resto del flow si falla (notificaciones, análisis CPO, etc.).
    """
    if not settings.roadmap_app_url:
        return
    if not settings.roadmap_supabase_url or not settings.ps_agent_email:
        return

    # Flatten grouped facts
    all_facts = [f for facts in grouped_facts.values() for f in facts]
    if not all_facts:
        return

    try:
        import roadmap_client
        import roadmap_support_client

        token = roadmap_client.login(
            supabase_url=settings.roadmap_supabase_url,
            anon_key=settings.roadmap_supabase_anon_key,
            email=settings.ps_agent_email,
            password=settings.ps_agent_password,
        )
        result = roadmap_support_client.sync_support_tickets(
            app_url=settings.roadmap_app_url,
            token=token,
            facts=all_facts,
        )
        print(f"[SUPPORT-SYNC] {result.synced} tickets sincronizados, {len(result.errors)} errores.")
        if result.errors:
            for err in result.errors[:5]:  # log primeros 5
                print(f"  [ERROR] {err.get('key')}: {err.get('message')}")
    except Exception as exc:
        print(f"[WARN] Sync de soporte falló: {exc}")
```

**Step 3: Verify imports**

Los módulos `roadmap_client` y `roadmap_support_client` deben ser importables. Existen en `src/`. Como otros imports en `main.py` ya hacen `from agent import run_agent` y `from jira_client import JiraClient`, el patrón de `import` plano debería funcionar igual.

**Step 4: Run full test suite**

```bash
./scripts/run-tests.sh
# Expected: all tests pass, including pre-existing + 7 new for support_client.
# IMPORTANT: si run_agent's signature cambió, los tests existentes que llaman a run_agent
# pueden romperse. Si pasa, hay que actualizar los unpacks en esos tests también.
```

Si rompen tests de `agent.py` o similares por la nueva signatura, agregarlos al fix:
- Buscar: `grep -rn "run_agent" tests/`
- Actualizar cada call site para esperar el nuevo tuple

**Step 5: Verify + commit**

```bash
git rev-parse --abbrev-ref HEAD  # MUST be feat/support-sync-client
git add src/agent.py src/main.py
# Si hubo que tocar tests:
# git add tests/...

git commit -m "feat(agent): sync support tickets to roadmap-app on each run"
```

---

## Task 4: Smoke test + push

**Files:** (verification only, no source changes unless something breaks)

**Step 1: Dry-run con `--roadmap-only --dry-run`**

```bash
cd "/Users/agusalvarez/Documents/Proyectos Vaas/.worktrees/feat-support-sync"  # o donde sea tu worktree
source .venv/bin/activate  # si no está activa
python src/main.py --roadmap-only --dry-run 2>&1 | tail -30
```

Verificar:
- El proceso termina sin excepciones
- Si hay tickets en el board, debería loggear `[SUPPORT-SYNC] N tickets sincronizados, 0 errores.` — esto SI llega a la red, lo cual con `--dry-run` igual ocurre (dry-run no aplica a roadmap-app HTTP, solo a Roam).
  - **Importante:** `--dry-run` en este agente solo evita enviar a Roam, NO bloquea HTTP a la roadmap-app. Si querés hacer un smoke 100% offline, comentar temporalmente la línea `_sync_support_tickets(...)` y descomentar después.

Si preferís NO pegarle a la roadmap-app durante el smoke, podés saltear este step y confiar en los unit tests.

**Step 2: Verificar que el sync efectivo funciona contra la roadmap-app productiva**

Solo si querés validar end-to-end con la API real:

```bash
python src/main.py --roadmap-only 2>&1 | grep -i "SUPPORT-SYNC"
# Expected output: "[SUPPORT-SYNC] N tickets sincronizados, 0 errores."
```

Después podés consultar Supabase para confirmar que la tabla `SupportTicket` tiene rows:
```sql
SELECT COUNT(*), MAX("lastSyncedAt") FROM "SupportTicket";
```

**Step 3: Push a main**

```bash
git rev-parse --abbrev-ref HEAD  # feat/support-sync-client
# Volver al worktree principal:
cd "/Users/agusalvarez/Documents/Proyectos Vaas"
git checkout main
git merge feat/support-sync-client
git push origin main
```

GitHub Actions tomará la nueva versión en la siguiente corrida del cron de `agent-monitor.yml` (cada 30 min).

**Step 4: Cleanup**

```bash
git worktree remove .worktrees/feat-support-sync
git branch -d feat/support-sync-client
```

---

## Notas finales

- El primer cron run después del merge será el backfill automático: el JQL actual del agente trae todos los tickets activos del board, y se pushean al endpoint en una sola corrida.
- Tickets cerrados antiguos (que ya no están en el board activo) NO se sincronizarán automáticamente — los Q anteriores van a quedar vacíos en el dashboard hasta que se haga un backfill manual con JQL ampliado (out of scope de este plan).
- Si `roadmap_app_url`, `roadmap_supabase_url`, o credenciales `ps_agent_*` no están en `.env`, el sync simplemente no corre (return silencioso) — el resto del agente sigue funcionando.
- El módulo `roadmap_support_client.py` es testeable de forma aislada: las 7 unit tests cubren payload shape, edge cases (criticality vacía, ticket abierto vs cerrado), partial errors, y propagación de HTTP errors.
