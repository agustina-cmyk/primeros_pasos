# Convenciones de Tests

> **Nota**: El proyecto no tiene tests aún. Este documento define las convenciones a seguir al implementarlos.

## Stack de testing

- **Test runner**: `pytest`
- **Fixtures**: usar `pytest` fixtures (`@pytest.fixture`, `tmp_path`, `monkeypatch`)
- **Mocking**: `unittest.mock` (`MagicMock`, `patch`) para dependencias externas
- **Sin dependencias adicionales** de testing por ahora (no coverage plugins, no factories)

Agregar a `requirements.txt` cuando se implemente:
```
pytest
```

## Estructura de archivos

```
tests/
├── test_classifier.py
├── test_planner.py
├── test_message_builder.py
├── test_memory.py
├── test_config.py
└── conftest.py          # Fixtures compartidos
```

Un archivo de test por módulo. Los tests van en `tests/` en la raíz del proyecto.

## Nomenclatura

- Archivo: `test_{nombre_modulo}.py`
- Función: `test_{función_que_se_testea}_{escenario}` o `test_{comportamiento_esperado}`

```python
# Correcto
def test_resolve_vertical_uses_prefix_first():
def test_resolve_vertical_falls_back_to_label_mapping():
def test_resolve_vertical_returns_sin_vertical_when_no_match():
def test_classify_tickets_marks_stale_when_no_change_in_stale_days():

# Evitar
def test_1():
def test_classifier():
def test_it_works():
```

## Estructura de un test

```python
def test_resolve_vertical_uses_prefix_first():
    # Arrange
    labels = ["vertical:pagos", "fefo-team"]
    label_prefix = "vertical:"
    label_to_vertical = {"fefo-team": "payments"}

    # Act
    result = resolve_vertical(labels, label_prefix, label_to_vertical)

    # Assert
    assert result == "pagos"
```

Usar el patrón Arrange / Act / Assert. No usar comentarios AAA explícitos si el test es corto.

## Fixtures compartidos (`conftest.py`)

Definir en `conftest.py` los builders de objetos de dominio más usados:

```python
import pytest
from models import TicketFacts, AgentMemoryState

@pytest.fixture
def base_ticket_facts():
    return TicketFacts(
        key="PS-123",
        vertical="payments",
        summary="Test ticket",
        status="In Progress",
        status_category="In Progress",
        assignee="John Doe",
        reporter="Jane Smith",
        created="2026-03-01T10:00:00.000+0000",
        updated="2026-03-15T10:00:00.000+0000",
        last_status_change_at="2026-03-01T10:00:00.000+0000",
        description="",
        section="",
        criticality="",
        environment="",
        ticket_type="Bug",
        url="https://pmvaas1.atlassian.net/browse/PS-123",
        labels=["fefo-team"],
        created_today=False,
        status_changed_today=False,
        finalized_today=False,
        is_stale=False,
        changed_since_last_run=True,
        status_changed=False,
        assignee_changed=False,
    )

@pytest.fixture
def empty_memory():
    return AgentMemoryState.empty()
```

## Uso de `monkeypatch` para env vars

```python
def test_load_settings_raises_when_jira_base_url_missing(monkeypatch):
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="JIRA_BASE_URL"):
        load_settings()
```

## Mocking de requests

```python
from unittest.mock import MagicMock, patch

def test_jira_client_search_tickets_returns_empty_on_no_issues():
    with patch("jira_client.requests.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.post.return_value.json.return_value = {"issues": [], "isLast": True}
        mock_session.post.return_value.raise_for_status.return_value = None

        client = JiraClient(base_url="https://example.com", email="a@b.com", api_token="token")
        result = client.search_tickets(jql="project = PS")

        assert result == []
```
