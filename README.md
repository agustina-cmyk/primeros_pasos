# Jira → Roam Agent

Agente en Python que monitorea el tablero de Production Support en Jira y actúa en dos frentes:

1. **Notificaciones a canales Roam** — informa novedades por vertical (tickets nuevos, resueltos, estancados) y un análisis de recurrencia para el CPO.
2. **Participación en el roadmap** — vota ideas, deja comentarios con evidencia de tickets reales y crea nuevas ideas cuando detecta necesidades no representadas.

## Scheduling (GitHub Actions)

| Workflow | Frecuencia | Modo |
|---|---|---|
| `agent-monitor.yml` | Cada 30 min | `--roadmap-only` — monitorea Jira y actúa en el roadmap |
| `agent-notify.yml` | Lun–Vie 17:00 GMT-2 | `--notify-only` — envía mensajes a los canales de Roam |

El estado del agente (`data/agent_state.json`) se persiste en git tras cada ejecución.

## Estructura

- `src/main.py` — punto de entrada y flags CLI
- `src/agent.py` — ciclo principal del agente
- `src/classifier.py` — transforma tickets en hechos (`new`, `needs_info`, `stale`, etc.)
- `src/jira_client.py` — lectura de tickets de Jira
- `src/planner.py` — decide acciones por vertical
- `src/message_builder.py` — arma los mensajes para Roam
- `src/recurrence_analyzer.py` — detecta patrones recurrentes vía LLM
- `src/roadmap_client.py` — cliente HTTP para la API del roadmAPP
- `src/roadmap_analyzer.py` — decide acciones en el roadmap vía LLM
- `src/roam_client.py` — envío de mensajes a Roam
- `src/memory.py` — persiste estado entre corridas
- `src/models.py` — modelos internos
- `src/config.py` — carga de variables de entorno

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Variables de entorno

### Jira
| Variable | Descripción |
|---|---|
| `JIRA_BASE_URL` | URL base de Jira (ej: `https://pmvaas1.atlassian.net`) |
| `JIRA_EMAIL` | Email del usuario de la API |
| `JIRA_API_TOKEN` | Token de API de Jira |
| `JIRA_CLOUD_ID` | Cloud ID de Atlassian |
| `JIRA_BOARD_ID` | ID del tablero a monitorear |
| `JIRA_JQL` | JQL custom (opcional, sobreescribe el board) |
| `JIRA_SECTION_FIELD` | Campo customfield de sección |
| `JIRA_CRITICALITY_FIELD` | Campo customfield de criticidad |
| `JIRA_ENVIRONMENT_FIELD` | Campo de ambiente |
| `JIRA_TYPE_FIELD` | Campo de tipo de issue |

### Roam
| Variable | Descripción |
|---|---|
| `ROAM_API_TOKEN` | Token de API de Roam |
| `ROAM_CHANNEL_IDS_JSON` | JSON con IDs de canal por vertical |
| `ROAM_CPO_CHANNEL_ID` | ID del canal del CPO |

### LLM
| Variable | Descripción |
|---|---|
| `LLM_WEBHOOK_URL` | Webhook de n8n para llamadas al LLM |

### RoadmAPP
| Variable | Descripción |
|---|---|
| `ROADMAP_APP_URL` | URL del roadmAPP (ej: `https://roadmap-app-vaas.vercel.app`) |
| `ROADMAP_SUPABASE_URL` | URL de Supabase del roadmAPP |
| `ROADMAP_SUPABASE_ANON_KEY` | Anon key de Supabase del roadmAPP |
| `PS_AGENT_EMAIL` | Email del agente en el roadmAPP |
| `PS_AGENT_PASSWORD` | Contraseña del agente en el roadmAPP |

## Ejecución

```bash
# Corrida completa (monitoreo + notificaciones + roadmap)
python src/main.py

# Solo roadmap: monitorea Jira y actúa en el roadmap sin enviar mensajes a canales
python src/main.py --roadmap-only

# Solo notificaciones: envía mensajes a los canales sin análisis de roadmap
python src/main.py --notify-only

# Forzar análisis de roadmap aunque no haya cambios en Jira
python src/main.py --roadmap-only --force-roadmap

# Solo el mensaje al canal del CPO
python src/main.py --cpo-only

# Previsualizar sin enviar nada
python src/main.py --dry-run
```

## Convenciones de vertical

Orden de resolución de la vertical de un ticket:
1. Etiqueta con prefijo `VERTICAL_LABEL_PREFIX` (default: `vertical:`)
2. Mapeo `LABEL_TO_VERTICAL_JSON`
3. Si no matchea nada: `sin_vertical`

## Módulo de roadmap

El agente participa en el [roadmAPP](https://roadmap-app-vaas.vercel.app) como representante de Production Support. En cada corrida puede:

- **Votar** ideas con evidencia de tickets reales (siempre deja un comentario explicando el porqué)
- **Comentar** ideas con contexto adicional de Jira
- **Crear** ideas nuevas cuando detecta un problema recurrente no representado en el roadmap

El análisis se activa automáticamente cuando:
- Hay tickets nuevos o con cambio de estado en Jira
- Hay ideas votadas por el agente que aún no tienen comentario de evidencia
- Hay comentarios de otros usuarios en ideas que el agente creó o votó

Las ideas creadas por el agente quedan con visibilidad `internal` (borrador) hasta que un admin las publique desde el roadmAPP.

## Notas

- La memoria se guarda en `data/agent_state.json` (trackeado en git).
- En `--dry-run` el agente no persiste memoria ni publica, solo muestra el plan.
- Si una vertical no tiene canal configurado, se salta sin error.
