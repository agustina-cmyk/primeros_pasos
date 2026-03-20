# Guías de Testing

> **Nota**: El proyecto no tiene tests aún. Este documento define la estrategia deseada a implementar.

## Objetivo

Cobertura del 80%+ en la lógica de negocio. Las capas de infraestructura (clientes HTTP) se testean con mocks.

## Estrategia por módulo

### `classifier.py` — Prioridad Alta

El módulo más crítico: convierte tickets raw en `TicketFacts` con flags de negocio. Cualquier bug aquí afecta todo el pipeline.

**Qué testear:**
- `resolve_vertical()`: todas las ramas de resolución (prefijo, mapeo, fallback `sin_vertical`).
- `classify_tickets()`: flags `created_today`, `finalized_today`, `is_stale`, `status_changed_today`.
- `classify_tickets()`: flags de comparación con memoria (`changed_since_last_run`, `status_changed`, `assignee_changed`).
- `_safe_parse_jira_datetime()`: formatos válidos, cadena vacía, formato inválido.
- `_is_same_local_day()`: mismo día, días distintos, valor `None`.

**Tipo de test:** unitario puro. No requiere mocks (no hay I/O).

### `planner.py` — Prioridad Alta

Determina qué acciones se comunican. Lógica simple pero crítica para el output.

**Qué testear:**
- Plan con tickets `created_today=True`.
- Plan con tickets `finalized_today=True`.
- Plan con tickets `is_stale=True`.
- Plan vacío: ningún flag activo → `actions == []`.
- Combinaciones: múltiples tipos de acción en el mismo plan.
- Orden de tickets dentro de cada acción (ordenados por `updated` desc).

**Tipo de test:** unitario puro.

### `message_builder.py` — Prioridad Media

Renderiza los mensajes. Los bugs aquí son visibles (mensajes incorrectos) pero no bloquean el pipeline.

**Qué testear:**
- `build_vertical_message()`: título correcto con counts, resumen de cambios presente.
- `_render_tickets()`: tickets con criticidad "Highest" tienen 🚨.
- `_render_tickets()` con `notify_stale_tickets`: mención a reporters al final.
- `_render_tickets()` con `notify_finished_today`: mención a reporters con ✅.
- Límite `max_items`: se trunca y se muestra "... y N más."
- `build_cpo_message()`: métricas globales correctas, desglose por vertical.
- `_format_last_run()`: hoy, ayer, fecha anterior, None.

**Tipo de test:** unitario puro.

### `memory.py` — Prioridad Media

**Qué testear:**
- `load()` cuando el archivo no existe → retorna `AgentMemoryState.empty()`.
- `load()` con archivo válido → desserializa correctamente.
- `load()` con campos desconocidos en el JSON → los ignora (compatibilidad forward).
- `save()` → crea el directorio si no existe, persiste el estado correctamente.

**Tipo de test:** unitario con filesystem real (usar `tmp_path` de pytest) o mock de `Path`.

### `config.py` — Prioridad Media

**Qué testear:**
- `_required()` lanza `ValueError` si la variable no está definida o está vacía.
- `_load_json_env()` parsea JSON válido, retorna `{}` si está vacía, lanza `ValueError` si no es JSON válido.
- `load_settings()` genera JQL automático cuando `JIRA_JQL` está vacío.

**Tipo de test:** unitario. Usar `monkeypatch` de pytest para setear env vars.

### `jira_client.py` y `roam_client.py` — Prioridad Baja

No requieren tests unitarios extensivos. Si se testean, usar mocks de `requests.Session`.

**Qué testear (opcional):**
- `_adf_to_text()`: ADF con texto anidado, nodo vacío, None.
- `_field_to_text()`: string, dict con key "value"/"name", lista, None.
- `_last_status_change_at()`: changelog con múltiples historias de estado.

### `recurrence_analyzer.py` — Prioridad Baja

Depende de la API de Anthropic. Si se testea, mockear `anthropic.Anthropic`.

**Qué testear (opcional):**
- Respuesta JSON válida → parsea correctamente a `RecurringPattern`.
- Respuesta con markdown code fence → se stripea correctamente.
- Grupos con 1 solo ticket → se filtran.

## Lo que NO testear

- `main.py`: es wiring de componentes. Testear con integración si es necesario, no unitario.
- `agent.py`: orquestación. Testear con mocks de los módulos individuales si se quiere cobertura.
- La lógica interna de Jira/Roam (responses HTTP): eso es responsabilidad de los SDKs.
