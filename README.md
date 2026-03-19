# Jira -> Roam Agent V1

Agente V1 en Python para:
1. Leer tickets de un tablero específico de Jira.
2. Segmentar por vertical según etiquetas.
3. Comparar contra corridas anteriores usando memoria local.
4. Decidir qué comunicar por vertical según reglas de negocio.
5. Enviar updates a distintos canales de Roam (vía webhook HTTP).

## Estructura

- `src/main.py`: punto de entrada y ejecución del agente.
- `src/agent.py`: ciclo principal del agente.
- `src/classifier.py`: transforma tickets en hechos útiles (`new`, `needs_info`, `stale`, etc.).
- `src/jira_client.py`: lectura de tickets en Jira.
- `src/planner.py`: decide acciones por vertical.
- `src/message_builder.py`: arma el mensaje final para Roam.
- `src/memory.py`: guarda y recupera estado entre corridas.
- `src/models.py`: modelos internos del agente.
- `src/roam_client.py`: envío del update a webhook de Roam.
- `src/config.py`: carga de variables de entorno.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Completa `.env` con:
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `JIRA_CLOUD_ID` si usas service accounts o scoped API tokens de Atlassian
- `JIRA_BOARD_ID` (o `JIRA_JQL` custom)
- `JIRA_SECTION_FIELD`, `JIRA_CRITICALITY_FIELD`, `JIRA_ENVIRONMENT_FIELD`, `JIRA_TYPE_FIELD`
- `ROAM_CHANNEL_URLS_JSON` con links de canal por vertical
- `VERTICAL_WEBHOOKS_JSON` con webhook por vertical
- `STALE_TICKET_DAYS` para tickets sin cambio de estado en los ultimos dias
- `AGENT_STATE_PATH` para la memoria local del agente
- opcional: `DEFAULT_ROAM_WEBHOOK`

## Convenciones de vertical

Orden de resolución:
1. Etiqueta con prefijo `VERTICAL_LABEL_PREFIX` (default: `vertical:`).
   Ejemplo: `vertical:pagos`.
2. Si no existe, mapeo `LABEL_TO_VERTICAL_JSON`.
3. Si no matchea nada: `sin_vertical`.

Configuracion actual del board fuente compartido por negocio:
- Board URL: `https://pmvaas1.atlassian.net/jira/software/projects/PS/boards/16`
- `JIRA_BASE_URL=https://pmvaas1.atlassian.net`
- `JIRA_CLOUD_ID=<pendiente si usamos service account token>`
- `JIRA_BOARD_ID=16`
- Verticales por labels:
- `payments`: `fefo-team`, `payments`
- `verification`: `eze-team`, `borbotones`
- `core`: `pablo-team`
- `fe`: `frontend`
- Canales Roam:
- `payments`: `https://ro.am/r/#/c/Ub93Cr5HRoSA5yd1Cj2shQ/bm9tc2cvbm90aHI`
- `verification`: `https://ro.am/r/#/c/zIPlNzFfRzGlVRto-Sdhag/bm9tc2cvbm90aHI`
- `core`: `https://ro.am/r/#/c/9tMTXH-EQ62S2VmAHfEaTg/bm9tc2cvbm90aHI`
- `fe`: `https://ro.am/r/#/c/prFFf-aKSjG0xJDdSdUjKA/bm9tc2cvbm90aHI`

## Decisiones del agente

En cada corrida el agente clasifica tickets y puede decidir acciones como:
- `notify_created_today`
- `notify_finished_today`
- `notify_stale_tickets`

Solo genera mensajes para verticales con acciones relevantes.

Reglas actuales:
- Tickets creados hoy: comparte status, resumen e informador.
- Tickets finalizados hoy: comparte detalle y menciona al informador.
- Tickets estancados: si no tuvieron cambio de estado en los ultimos 15 dias, comparte detalle y agrega una consulta abierta al canal.
- Todos los tickets salen con link directo al issue en Jira.
- El resumen usa descripcion, seccion, criticidad, ambiente y tipo cuando esos campos esten disponibles en Jira.

## Ejecución

```bash
python src/main.py
```

Previsualizar mensaje sin enviar a Roam:

```bash
python src/main.py --dry-run
```

## Ejemplo de configuración

```env
JIRA_BASE_URL=https://pmvaas1.atlassian.net
JIRA_CLOUD_ID=<cloud-id>
JIRA_EMAIL=bot@acme.com
JIRA_API_TOKEN=xxx
JIRA_BOARD_ID=16
JIRA_SECTION_FIELD=customfield_12345
JIRA_CRITICALITY_FIELD=customfield_45678
JIRA_ENVIRONMENT_FIELD=environment
JIRA_TYPE_FIELD=issuetype
VERTICAL_LABEL_PREFIX=vertical:
LABEL_TO_VERTICAL_JSON={"fefo-team":"payments","payments":"payments","eze-team":"verification","borbotones":"verification","pablo-team":"core","frontend":"fe"}
ROAM_CHANNEL_URLS_JSON={"payments":"https://ro.am/r/#/c/Ub93Cr5HRoSA5yd1Cj2shQ/bm9tc2cvbm90aHI","verification":"https://ro.am/r/#/c/zIPlNzFfRzGlVRto-Sdhag/bm9tc2cvbm90aHI","core":"https://ro.am/r/#/c/9tMTXH-EQ62S2VmAHfEaTg/bm9tc2cvbm90aHI","fe":"https://ro.am/r/#/c/prFFf-aKSjG0xJDdSdUjKA/bm9tc2cvbm90aHI"}
VERTICAL_WEBHOOKS_JSON={"payments":"https://roam/channel-payments","verification":"https://roam/channel-verification","core":"https://roam/channel-core","fe":"https://roam/channel-fe"}
DEFAULT_ROAM_WEBHOOK=https://roam/general
STALE_TICKET_DAYS=15
```

## Notas

- El payload enviado a webhook es:
  - `title`: resumen corto por vertical.
  - `body`: secciones según las acciones decididas por el agente.
- `ROAM_CHANNEL_URLS_JSON` guarda links humanos de los canales y se incluyen en el mensaje/dry-run.
- `VERTICAL_WEBHOOKS_JSON` sigue reservado para endpoints reales de publicacion.
- La memoria queda guardada por default en `data/agent_state.json`.
- Si una vertical no tiene webhook específico ni `DEFAULT_ROAM_WEBHOOK`, se salta.
- En `--dry-run` el agente no persiste memoria ni publica, solo muestra el plan y el mensaje.
