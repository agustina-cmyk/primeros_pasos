# Convenciones de Código

Patrones usados en `src/` para mantener consistencia entre módulos.

## Lenguaje y estilo

- Python 3.13. Type hints en todas las funciones y métodos.
- snake_case para variables, funciones y módulos. PascalCase para clases.
- Sin framework web ni ORM. Scripts puros con stdlib + `requests` + `python-dotenv` + `anthropic`.

## Dataclasses

### Regla: inmutable vs mutable

| Caso                                    | Usar                    |
|-----------------------------------------|-------------------------|
| Datos que no cambian después de crearse | `@dataclass(frozen=True)` |
| Estado que se modifica en el tiempo     | `@dataclass` (mutable)  |

**Inmutables** (`frozen=True`): `JiraTicket`, `JiraBoardContext`, `TicketFacts`, `AgentAction`, `VerticalPlan`, `Settings`.

**Mutables**: `TicketStateSnapshot`, `AgentMemoryState` (porque `save()` actualiza `last_run_at` in-place).

```python
# Correcto: datos de dominio derivados → frozen
@dataclass(frozen=True)
class TicketFacts:
    key: str
    vertical: str
    is_stale: bool
    # ...

# Correcto: estado que se actualiza → mutable
@dataclass
class AgentMemoryState:
    tickets: Dict[str, TicketStateSnapshot]
    last_run_at: Optional[str] = None
```

## Variables de entorno

- Variables requeridas: usar `_required(var_name)` → lanza `ValueError` si está vacía.
- Variables JSON: usar `_load_json_env(var_name)` → retorna `Dict[str, str]`, keys y values en lowercase.
- Variables opcionales con default: `os.getenv("VAR", "default").strip()`.

```python
# Requerida
jira_base_url = _required("JIRA_BASE_URL").rstrip("/")

# JSON opcional
label_to_vertical = _load_json_env("LABEL_TO_VERTICAL_JSON")  # {} si no está

# Con default
max_results = int(os.getenv("JIRA_MAX_RESULTS", "100"))
```

Toda la carga de config ocurre en `config.py`. El resto del código recibe un `Settings` ya construido.

## Manejo de errores

- Los clientes externos (`JiraClient`, `RoamClient`) dejan propagar las excepciones HTTP (`resp.raise_for_status()`).
- El orquestador (`agent.py`, `main.py`) captura con `try/except` y continúa con `[WARN]` cuando el fallo es no crítico.
- Nunca silenciar errores sin al menos imprimir el motivo.

```python
# Correcto: fallo no-crítico en análisis opcional → warn y continuar
try:
    recurring_patterns = analyze_recurrence(...)
except Exception as exc:
    print(f"[WARN] Análisis de recurrencia falló: {exc}")

# Incorrecto: silenciar sin log
try:
    do_something()
except Exception:
    pass
```

## Separación de responsabilidades

- `classifier.py`, `planner.py`, `message_builder.py` son funciones puras: reciben datos, retornan resultados. **No importan `config.py` ni clientes HTTP**.
- `agent.py` orquesta pero no envía mensajes — eso lo hace `main.py`.
- `main.py` es el único lugar donde se decide si enviar por channel ID, webhook o saltar.

```python
# Correcto: classifier recibe parámetros, no Settings
def classify_tickets(
    tickets: List[JiraTicket],
    memory_state: AgentMemoryState,
    label_prefix: str,
    label_to_vertical: Dict[str, str],
    stale_ticket_days: int,
) -> Dict[str, List[TicketFacts]]:
    ...
```

## Imports

- Imports relativos: no se usan (el proyecto corre desde `src/` directamente).
- Imports opcionales dentro de funciones: se usan para dependencias opcionales que pueden no estar disponibles.

```python
# En agent.py: import dentro de función para feature opcional
if settings.anthropic_api_key:
    from recurrence_analyzer import analyze_recurrence
    recurring_patterns = analyze_recurrence(...)
```

## Serialización / deserialización

- `models.py` define `to_dict()` y `@classmethod empty()` en `AgentMemoryState`.
- `memory.py` usa `dataclasses.asdict()` para serializar `TicketStateSnapshot`.
- Al deserializar, siempre filtrar keys desconocidas para compatibilidad forward:

```python
allowed_fields = {field.name for field in fields(TicketStateSnapshot)}
payload = {k: v for k, v in value.items() if k in allowed_fields}
tickets[key] = TicketStateSnapshot(**payload)
```
