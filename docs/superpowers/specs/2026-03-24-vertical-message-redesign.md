# Spec: Rediseño del mensaje vertical — modelo completo de estado del tablero

**Fecha:** 2026-03-24
**Estado:** Aprobado por usuario

---

## Problema

El sistema actual de mensajes verticales es evento-driven: solo notifica cuando un ticket cumple una condición explícita (`created_today`, `status_changed`, `finalized_today`, `is_stale` con umbral de 15 días). Esto genera un gap de visibilidad: tickets activos sin cambio de estado entre el día de creación y el día 15 son completamente invisibles en el canal. Ejemplo real: PS-1364 (creado el 23/03, To Do, sin cambio) no aparece en ningún mensaje hasta el día 15.

---

## Solución

Cambiar el modelo de "notificación de eventos" a "reporte de estado completo del vertical". Cada corrida del agente produce un mensaje que refleja el estado actual del tablero: qué cambió, qué está sin movimiento reciente, y qué lleva más de 5 días parado.

---

## Diseño

### 1. Nuevo campo en `TicketFacts`

Agregar `days_without_status_change: int` calculado en `classifier.py` como la diferencia en días calendario entre `last_status_change_at` y la fecha actual (Argentina TZ), usando `floor` de la diferencia de fechas (mismo patrón que `_is_same_local_day`).

**Fallback para `last_status_change_at` nulo:** usar la fecha de creación del ticket (`created`) como ancla. Esto refleja la realidad: si nunca hubo un cambio de estado registrado, el ticket lleva parado desde su creación. Si `created` también es nulo, usar `999` como sentinel para forzar el ticket al bucket `notify_unchanged_stale`.

**Sentinel en el rendering:** cuando `days_without_status_change == 999`, mostrar `–` en lugar de `999d` en el cuerpo del mensaje, para que no parezca un bug.

Los campos `created_today`, `finalized_today` y `status_changed` se conservan — se usan para el rendering dentro de la sección de cambios.

**Campo `status_changed_today`:** este campo existente en `TicketFacts` (línea 26 de `models.py`) queda **eliminado**. Con el nuevo modelo, la distinción de si el cambio fue "hoy" versus "desde el último run" no es necesaria — `status_changed` (comparación contra memoria) es suficiente. El rendering de si un ticket finalizó hoy se hace via `finalized_today`, no via `status_changed_today`.

### 2. Nuevos action types (reemplazan los 5 actuales)

| Action type | Condición | Reemplaza |
|---|---|---|
| `notify_changes` | `status_changed == True` OR `created_today == True` OR `finalized_today == True` | `notify_created_today` + `notify_finished_today` + `notify_status_changed` |
| `notify_unchanged_recent` | no aparece en `notify_changes`, `days_without_status_change < 5` | — (nuevo) |
| `notify_unchanged_stale` | no aparece en `notify_changes`, `days_without_status_change >= 5` | `notify_stale_tickets` |

**Regla de exclusión mutua:** un ticket que califica para `notify_changes` no puede aparecer en `notify_unchanged_recent` ni en `notify_unchanged_stale`. Los buckets de "sin movimiento" contienen únicamente tickets que no cumplen ninguna condición de `notify_changes`.

**Tickets done:** los tickets con `status_category == "done"` y `finalized_today == False` quedan excluidos de todas las secciones. El JQL del agente trae tickets done actualizados hoy (comentarios, etc.), pero si no finalizaron hoy no son novedades — excluirlos es correcto y este comportamiento es intencional.

**Tickets finalized_today en buckets unchanged:** un ticket que finalizó hoy tiene `finalized_today == True`, por lo tanto cae siempre en `notify_changes` y nunca en los buckets de "sin movimiento", aunque `days_without_status_change` sea 0.

### 3. Ordenamiento y cap de `notify_unchanged_stale`

1. Críticos (`criticality == "highest"`) primero, ordenados por `days_without_status_change` descendente (más viejos primero dentro del grupo crítico)
2. Resto: ordenados por `days_without_status_change` descendente (más viejos primero — los más urgentes según antigüedad)
3. Cap: `MAX_ITEMS_PER_VERTICAL` (default 20); si hay más, agregar línea con conteo y link al board

> **Nota:** este orden (más viejos primero dentro de cada grupo) es el mismo que usa el mensaje CPO en su sección "sin movimiento más prolongado". La formulación anterior del diseño ("más recientemente cambiados primero") fue incorrecta y ha sido corregida aquí.

### 4. Formato del mensaje

**Título:**
```
[Jira Agent] PS | Vertical: {vertical} | {status}: {N} · {status}: {N} · ...
```
Solo estados activos (no-done, excepto `finalized_today`), ordenados por frecuencia descendente. Si no hay tickets activos para el vertical, mostrar `Sin tickets activos`.

**Cuerpo:**
```
🔄 Cambios desde {last_run_label} (N)
  [ordenados por updated desc]

- [PS-XXXX](url) 🆕/✅ 🚨 — Summary
  {status} | @reporter

_{reporter}: sus tickets fueron cerrados hoy_ ✅   ← solo si hay finalizados

_Sin cambios de estado desde {last_run_label}._   ← si N == 0

---

📋 Sin movimiento — menos de 5 días (N)
  [ordenados por days_without_status_change asc]

- [PS-XXXX](url) 🚨 — Summary
  {status} · {N}d | @reporter

_Ninguno._   ← si N == 0

---

⏳ Sin movimiento — más de 5 días (N)
  [críticos primero, luego por days_without_status_change desc]

- [PS-XXXX](url) 🚨 — Summary
  {status} · {N}d | @reporter   ← mostrar "–" si sentinel 999

_Ninguno._   ← si N == 0

_... y N más. [Ver tablero →](board_url)_   ← si hay cap y board_url configurada

_{reporters}: ¿estos tickets siguen siendo necesarios?..._
```

### 5. Cambios de configuración

| Variable | Cambio |
|---|---|
| `STALE_TICKET_DAYS` | Renombrar a `UNCHANGED_STALE_DAYS`, cambiar default a `5` |
| `JIRA_BOARD_URL` | Nueva variable opcional global; apunta al tablero Jira del proyecto. Se usa como link al pie de `notify_unchanged_stale` cuando hay cap. Es un único link global (no por vertical). Si en el futuro se necesitan links por vertical, se puede extender con `JIRA_BOARD_URLS_JSON`. |

> **Impacto en el mensaje CPO:** `build_cpo_message` usa `is_stale` extensivamente (conteos, listados, señales para el roadmap). Con el cambio de umbral de 15 → 5 días, todas esas métricas cambian de significado. Esto es **intencional** — el CPO debe ver la misma definición de "sin movimiento" que los canales verticales. Como consecuencia, el número de tickets "estancados" en el reporte CPO aumentará significativamente.

### 6. Fix incluido: dry-run mostraba mensajes verticales vacíos

`skip_channels = roadmap_only or dry_run` hacía que el loop de envío iterara sobre `[]` en dry-run, por lo que nunca se imprimía el preview. Corregido a `skip_channels = roadmap_only`. Ya aplicado.

---

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `src/models.py` | Agregar campo `days_without_status_change: int` a `TicketFacts`; eliminar campo `status_changed_today` |
| `src/classifier.py` | Calcular `days_without_status_change`; actualizar `is_stale` para usar nuevo umbral |
| `src/planner.py` | Reemplazar 5 action types por 3 nuevos; nueva lógica de ordenamiento para `notify_unchanged_stale` |
| `src/message_builder.py` | Nuevo formato de título (distribución por estado) + 3 secciones nuevas + link al board |
| `src/config.py` | Renombrar `stale_ticket_days` → `unchanged_stale_days`; agregar `jira_board_url` |
| `src/agent.py` | Actualizar call sites: `settings.stale_ticket_days` → `settings.unchanged_stale_days` (líneas 25, 97); agregar `board_url` a la llamada de `build_vertical_message` |
| `.env` | Renombrar `STALE_TICKET_DAYS` → `UNCHANGED_STALE_DAYS`; agregar `JIRA_BOARD_URL` (opcional) |
| `tests/` | Agregar/actualizar tests de `classifier` (nuevo campo, fallback, sentinel), `planner` (3 nuevos action types, mutual exclusion), `message_builder` (nuevo formato, 3 secciones, cap con link) |

---

## Lo que NO cambia

- Lógica de envío a Roam (channels, webhooks, fallbacks)
- Código de `build_cpo_message` — no requiere modificaciones de código, pero sus métricas cambian numéricamente por el nuevo umbral de `is_stale` (ver Sección 5)
- Lógica del agente roadmap
- Memoria del agente (`agent_state.json`)
- Menciones a reporters en `notify_unchanged_stale` — se mantienen igual que en el actual `notify_stale_tickets`
- `notify_unchanged_recent` no incluye menciones a reporters por diseño: son tickets demasiado recientes para considerar que están "sin atender"

---

## Prototipo validado

Se validó el formato con datos reales de Jira via `scripts/preview_new_format.py`. PS-1364 aparece correctamente en "Sin movimiento — menos de 5 días · 1d" bajo `verification`.
