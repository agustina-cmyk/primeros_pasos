# Variables de Entorno

Todas las variables de configuración del agente. Definidas en `.env` (copiado de `.env.example`).

## Jira

| Variable                 | Requerida | Default                         | Descripción                                                                 |
|--------------------------|-----------|---------------------------------|-----------------------------------------------------------------------------|
| `JIRA_BASE_URL`          | ✅        | —                               | URL base de Jira. Ej: `https://pmvaas1.atlassian.net`                      |
| `JIRA_EMAIL`             | ✅        | —                               | Email del usuario de Jira con acceso al board.                             |
| `JIRA_API_TOKEN`         | ✅        | —                               | API token de Jira (generado en Atlassian account settings).                |
| `JIRA_BOARD_ID`          | ✅        | —                               | ID numérico del board. Ej: `16`                                            |
| `JIRA_CLOUD_ID`          | ❌        | `""`                            | Cloud ID de Atlassian. Requerido para service accounts / scoped tokens.    |
| `JIRA_BASE_JQL`          | ❌        | `board = {JIRA_BOARD_ID}`       | Filtro "qué tickets le importan a este agente", SIN filtros de recencia ni estado. Se reusa para el daily (agrega recency) y para el search de tickets finalizados (agrega `statusCategory = Done AND updated >= -Nd`). Ej: `project = PS`. |
| `JIRA_JQL`               | ❌        | Auto-generado desde BASE_JQL    | JQL del fetch diario (activos + finalizados hoy). Si está vacío se genera: `({JIRA_BASE_JQL}) AND (statusCategory != Done OR updatedDate >= startOfDay()) ORDER BY updated DESC` |
| `JIRA_MAX_RESULTS`       | ❌        | `100`                           | Máximo de tickets por corrida.                                             |
| `JIRA_SECTION_FIELD`     | ❌        | `""`                            | Campo custom de Jira para "sección". Ej: `customfield_12345`               |
| `JIRA_CRITICALITY_FIELD` | ❌        | `""` (usa `priority`)           | Campo custom para criticidad. Si está vacío usa el campo `priority`.       |
| `JIRA_ENVIRONMENT_FIELD` | ❌        | `environment`                   | Campo de Jira para el ambiente del ticket.                                 |
| `JIRA_TYPE_FIELD`        | ❌        | `issuetype`                     | Campo de Jira para el tipo de ticket.                                      |

## Clasificación de verticales

| Variable                  | Requerida | Default         | Descripción                                                                   |
|---------------------------|-----------|-----------------|-------------------------------------------------------------------------------|
| `VERTICAL_LABEL_PREFIX`   | ❌        | `vertical:`     | Prefijo de label para resolver vertical. Ej: `vertical:pagos` → `pagos`.    |
| `LABEL_TO_VERTICAL_JSON`  | ❌        | `{}`            | JSON: mapeo de label → nombre de vertical. Ej: `{"fefo-team":"payments"}`. Keys y values se normalizan a lowercase. |

## Roam

| Variable                  | Requerida | Default | Descripción                                                                   |
|---------------------------|-----------|---------|-------------------------------------------------------------------------------|
| `ROAM_API_TOKEN`          | ❌        | `""`    | Bearer token para la Roam API. Requerido para enviar por channel ID.         |
| `ROAM_CHANNEL_IDS_JSON`   | ❌        | `{}`    | JSON: mapeo vertical → channel ID. Ej: `{"payments":"C-xxxx..."}`. Método preferido de envío. |
| `ROAM_CHANNEL_URLS_JSON`  | ❌        | `{}`    | JSON: mapeo vertical → URL web del canal. Solo referencia visual en dry-run. |
| `ROAM_CPO_CHANNEL_ID`     | ❌        | `""`    | Channel ID del canal CPO. Si está configurado, se envía el análisis ejecutivo. |
| `VERTICAL_WEBHOOKS_JSON`  | ❌        | `{}`    | JSON: mapeo vertical → webhook URL. Fallback si no hay channel ID.           |
| `DEFAULT_ROAM_WEBHOOK`    | ❌        | `""`    | Webhook fallback global si no hay webhook específico para la vertical.        |

## Análisis IA (opcional)

| Variable                    | Requerida | Default | Descripción                                                                 |
|-----------------------------|-----------|---------|-----------------------------------------------------------------------------|
| `ANTHROPIC_API_KEY`         | ❌        | `""`    | API key de Anthropic. Habilita el análisis de patrones recurrentes.        |
| `RECURRENCE_LOOKBACK_DAYS`  | ❌        | `90`    | Días hacia atrás para buscar tickets finalizados en el análisis de recurrencia. |

## Comportamiento del agente

| Variable                  | Requerida | Default                   | Descripción                                                               |
|---------------------------|-----------|---------------------------|---------------------------------------------------------------------------|
| `STALE_TICKET_DAYS`       | ❌        | `15`                      | Días sin cambio de estado para considerar un ticket como estancado.      |
| `MAX_ITEMS_PER_VERTICAL`  | ❌        | `20`                      | Máximo de tickets listados por vertical en el mensaje.                   |
| `AGENT_STATE_PATH`        | ❌        | `data/agent_state.json`   | Ruta al archivo de memoria del agente.                                   |

## Módulo de roadmap (opcional)

Si estas variables no están configuradas, el módulo de roadmap se saltea silenciosamente.

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `ROADMAP_APP_URL` | No | URL base de la aplicación de roadmap (ej: `https://roadmap-app-vaas.vercel.app`) |
| `ROADMAP_SUPABASE_URL` | No | URL del proyecto Supabase del roadmap (Settings → API en el dashboard) |
| `ROADMAP_SUPABASE_ANON_KEY` | No | Anon key del proyecto Supabase del roadmap |
| `PS_AGENT_EMAIL` | No | Email del usuario del agente en el roadmap (ej: `ps_agent@getvaas.com`) |
| `PS_AGENT_PASSWORD` | No | Contraseña del usuario del agente en el roadmap |

## Notas

- Las variables JSON se parsean con `json.loads()`. Un valor vacío o `{}` equivale a dict vacío.
- Si `JIRA_CLOUD_ID` está configurado, las llamadas a la API usan `https://api.atlassian.com/ex/jira/{cloud_id}/...` en lugar de `JIRA_BASE_URL`.
- El canal CPO requiere `ROAM_CPO_CHANNEL_ID` y `ROAM_API_TOKEN`. Sin ambos no se envía.
