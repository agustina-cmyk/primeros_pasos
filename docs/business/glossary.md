# Glosario de Dominio

Términos de negocio usados en el proyecto y su significado en el contexto del agente.

## Entidades principales

| Término              | Definición                                                                                     |
|----------------------|-----------------------------------------------------------------------------------------------|
| **Vertical**         | Equipo de negocio al que pertenece un ticket. Se resuelve desde las labels del ticket en Jira. Ejemplos: `payments`, `verification`, `core`, `fe`. |
| **Ticket**           | Issue de Jira. En el agente se representa como `JiraTicket` (raw) o `TicketFacts` (clasificado). |
| **TicketFacts**      | Representación enriquecida de un ticket con todos los flags computados. Inmutable (`frozen=True`). |
| **VerticalPlan**     | Conjunto de acciones decididas para una vertical en una corrida del agente.                   |
| **AgentAction**      | Una acción concreta dentro de un plan. Tiene un `action_type` y la lista de tickets que la generan. |
| **Memoria del agente** | Estado persistido en `data/agent_state.json` que el agente usa para comparar entre corridas. |

## Flags de ticket (`TicketFacts`)

| Flag                    | Definición                                                                                  |
|-------------------------|--------------------------------------------------------------------------------------------|
| `created_today`         | El ticket fue creado en el día local actual.                                               |
| `finalized_today`       | El ticket tiene `status_category = Done` y cambió de estado hoy.                          |
| `is_stale`              | El ticket no tuvo cambio de estado en los últimos N días (`STALE_TICKET_DAYS`, default 15). |
| `status_changed_today`  | El estado del ticket cambió hoy (independiente de si finalizó).                            |
| `changed_since_last_run`| El ticket fue modificado desde la última corrida del agente (status, assignee o updated). |
| `status_changed`        | El estado cambió respecto al snapshot guardado en memoria.                                 |
| `assignee_changed`      | El responsable cambió respecto al snapshot en memoria.                                     |

## Resolución de vertical

Orden de prioridad para asignar vertical a un ticket:

1. Label con prefijo `VERTICAL_LABEL_PREFIX` (default: `vertical:`). Ejemplo: `vertical:pagos` → vertical `pagos`.
2. Mapeo explícito `LABEL_TO_VERTICAL_JSON`: label exacta → nombre de vertical.
3. Si ninguna label hace match: vertical `sin_vertical`.

## Verticales del board PS (configuración actual)

| Label en Jira         | Vertical     |
|-----------------------|-------------|
| `fefo-team`, `payments` | `payments`  |
| `eze-team`, `borbotones` | `verification` |
| `pablo-team`          | `core`      |
| `frontend`            | `fe`        |

## Tipos de acción

| `action_type`             | Cuándo se genera                                                          |
|---------------------------|---------------------------------------------------------------------------|
| `notify_created_today`    | Hay al menos un ticket con `created_today=True`.                          |
| `notify_finished_today`   | Hay al menos un ticket con `finalized_today=True`.                        |
| `notify_stale_tickets`    | Hay al menos un ticket con `is_stale=True`.                               |

## Canales de Roam

Cada vertical tiene un canal destino en Roam. Los mensajes se envían via:
- **API Bearer** (`ROAM_CHANNEL_IDS_JSON`): método preferido. Usa `POST /v1/chat.sendMessage`.
- **Webhook URL** (`VERTICAL_WEBHOOKS_JSON` o `DEFAULT_ROAM_WEBHOOK`): fallback.
- **CPO channel** (`ROAM_CPO_CHANNEL_ID`): canal ejecutivo con análisis global + patrones recurrentes.
