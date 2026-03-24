# Spec: Mensaje CPO semanal y ciclo semanal del roadmap agent

**Fecha:** 2026-03-24
**Estado:** Aprobado por usuario

---

## Problema

El mensaje CPO actual es un snapshot del momento en que corre el agente: refleja el estado instantáneo del tablero, sin ventana temporal. Esto limita su utilidad para el C-level, que necesita entender la evolución de la semana: cuánto se movió, cuánto tardamos en resolver, qué patrones persisten. Además, el roadmap agent (`ps_agent`) corre en cada corrida con cambios, generando ruido y sin coherencia semanal.

---

## Solución

1. Reemplazar el mensaje CPO diario por un **mensaje semanal** que agrega datos de toda la semana (lunes a viernes).
2. Alinear el roadmap agent al mismo ciclo: corre solo los viernes, junto con el mensaje CPO.
3. El agente acumula snapshots diarios en `agent_state.json` para habilitar métricas de trazabilidad (tiempo en estado, velocidad de resolución).

---

## Arquitectura del ciclo

### Corridas diarias (lunes a jueves)
- Mensajes verticales a Roam: **sin cambios**.
- `recurrence_analyzer`: sigue corriendo siempre (su output alimenta el mensaje del viernes).
- Roadmap agent: **skip**.
- Mensaje CPO: **skip**. La función `run_agent()` ya no retorna `cpo_body` en corridas no-semanales; `main.py` no intenta enviarlo.
- Al final: guardar snapshot de tickets activos en `weekly_buffer` de `agent_state.json`.

### Corrida del viernes (17:00 AR)
- Mensajes verticales a Roam: **sin cambios**.
- `recurrence_analyzer`: corre normalmente.
- Construir y enviar **mensaje CPO semanal** al canal `ROAM_CPO_CHANNEL_ID`.
- Correr **roadmap agent** (`roadmap_analyzer`).
- Guardar snapshot del viernes en `weekly_buffer`.
- Limpiar `weekly_buffer` y registrar `weekly_last_run_at`.

### Detección del viernes
El agente evalúa `datetime.now(AR_TZ).weekday() == 4`. Sin config adicional.

### Buffer stale — recuperación ante fallo del viernes
En cada corrida, antes de guardar el snapshot, el agente verifica si el buffer pertenece a la semana ISO actual (comparando la fecha del primer snapshot guardado con `datetime.now(AR_TZ).isocalendar().week`). Si pertenece a una semana anterior, el buffer se limpia antes de guardar el snapshot nuevo. Esto evita que un viernes fallido contamine la semana siguiente.

### Flag `--weekly`
Para forzar la corrida semanal en cualquier día (testing):
```
python src/main.py --weekly
```

Comportamiento combinado con otros flags:
- `--weekly --dry-run`: imprime el mensaje CPO semanal en stdout sin enviarlo a Roam, sin guardar snapshot, sin limpiar el buffer, sin generar el HTML report. El roadmap agent se imprime en dry-run (sin ejecutar acciones).
- `--weekly --notify-only`: envía el mensaje CPO semanal, pero **no** corre el roadmap agent (consistente con el comportamiento de `--notify-only` en corridas normales).

---

## Schema del `weekly_buffer`

Nueva sección en `agent_state.json`:

```json
{
  "weekly_buffer": {
    "2026-03-18": {
      "PS-1364": {
        "status": "To Do",
        "status_category": "new",
        "days_without_status_change": 1,
        "is_stale": false,
        "criticality": null,
        "vertical": "verification",
        "reporter": "jdoe",
        "created": "2026-03-15T10:30:00.000+0000",
        "finalized_today": false
      }
    },
    "2026-03-19": { ... }
  },
  "weekly_last_run_at": "2026-03-21T17:02:00-03:00"
}
```

**Campos clave:**
- `created`: datetime de creación del ticket en Jira, tal como viene de `TicketFacts.created` (formato ISO 8601, ej. `"2026-03-15T10:30:00.000+0000"`). Se almacena sin truncar para preservar precisión al calcular tiempo de resolución en Bloque 2.
- `finalized_today`: flag booleano del día. Se almacena directamente desde `TicketFacts.finalized_today` para que el agregado del viernes pueda sumar tickets resueltos por día sin necesidad de inferirlos por ausencia.

**Estimación de tamaño:** ~250 bytes por ticket × 100 tickets × 5 días ≈ 125KB máximo por semana. Sin impacto.

Cada snapshot solo incluye tickets activos al momento de la corrida (misma lista que ya se clasifica).

---

## Contenido del mensaje CPO semanal

El mensaje reemplaza a `build_cpo_message`. Se envía al canal `ROAM_CPO_CHANNEL_ID` en formato Roam markdown.

### Bloque 1 — Resumen ejecutivo
Métricas del período lunes–viernes:
- Tickets activos al inicio vs al cierre de la semana (comparando primer y último snapshot del buffer)
- Tickets creados durante la semana: tickets presentes en algún snapshot del buffer pero ausentes en el primero (incluye tickets creados y resueltos en la misma semana)
- Tickets resueltos durante la semana (suma de `finalized_today == True` a través de todos los snapshots del buffer)
- Tickets sin ningún movimiento durante toda la semana (tickets cuyo `status` no cambia entre el primer y último snapshot)
- Tickets críticos (Highest) activos al cierre

### Bloque 2 — Velocidad del equipo
Calculado desde los snapshots diarios:
- **Tiempo promedio de resolución:** para tickets con `finalized_today == True` en algún snapshot de la semana, se calcula `fecha_finalizacion - created` usando el campo `created` del buffer.
- **Tickets que avanzaron de estado:** tickets cuyo campo `status` difiere entre al menos dos entradas del buffer (comparación cross-day por `ticket_key`). Agrupados por vertical.
- **Tickets sin movimiento:** tickets cuyo `status` es idéntico en todos los snapshots del buffer donde aparecen. Agrupados por vertical.

### Bloque 3 — Patrones recurrentes
Output del `recurrence_analyzer` (LLM). Sin cambios en este módulo.

### Bloque 4 — Señales para el roadmap
Calculadas sobre la ventana semanal (no el snapshot del momento):
- Vertical con mayor carga estancada al cierre
- Tickets Highest activos
- Tickets sin movimiento hace más de N días (usando `days_without_status_change` del snapshot del viernes)

---

## Cambios por módulo

| Módulo | Cambio |
|--------|--------|
| `src/memory.py` | Agregar `save_weekly_snapshot(date, tickets)`, `get_weekly_buffer()`, `clear_weekly_buffer()`, `get_weekly_last_run_at()`, y la lógica de detección de buffer stale (semana ISO distinta → limpiar antes de guardar) |
| `src/message_builder.py` | Agregar `build_weekly_cpo_message(buffer, patterns)`. `build_cpo_message` se puede eliminar — ya no se llama desde `agent.py` |
| `src/agent.py` | Guardar snapshot al final de cada corrida. Si viernes (o `--weekly`): construir mensaje CPO semanal + correr roadmap agent. En corridas normales: skip de ambos. `run_agent()` solo retorna `cpo_body` en corridas semanales |
| `src/main.py` | Agregar flag `--weekly` con el comportamiento detallado arriba |

## Lo que NO cambia

- Mensajes verticales — sin cambios, corren todos los días
- `recurrence_analyzer.py` — sigue corriendo siempre
- `roadmap_client.py`, `jira_client.py`, `roam_client.py`
- Lógica interna del roadmap agent — solo cambia cuándo se invoca
- Formato Roam del mensaje (markdown)
- `agent_state.json` — solo se agrega una nueva sección `weekly_buffer` y `weekly_last_run_at`; el resto no cambia

---

## Schedule

El agente ya tiene un job diario. Solo ajustar el job del viernes para que corra a las 17:00 AR. El código detecta el día automáticamente — no requiere configuración nueva en el agente.
