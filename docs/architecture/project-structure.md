# Estructura del Proyecto

Agente Python que lee tickets de Jira, los clasifica por vertical y envía actualizaciones a canales de Roam.

## Árbol de carpetas

```
Proyectos Vaas/
├── src/                    # Código fuente (todos los módulos en flat)
├── data/                   # Estado persistido del agente entre corridas
│   └── agent_state.json    # Memoria del agente (ver docs/configuration/key-files.md)
├── output/                 # Archivos de salida (PDFs, reportes, etc.)
├── tmp/                    # Archivos temporales
├── scripts/                # Scripts de ejecución y testing (Docker)
├── requirements.txt        # Dependencias Python
├── .env / .env.example     # Variables de entorno
└── .sdd.json               # Configuración del workflow SDD
```

## Módulos en `src/`

| Módulo                  | Responsabilidad                                                                 |
|-------------------------|---------------------------------------------------------------------------------|
| `main.py`               | Entry point. CLI args, wiring de componentes, envío a Roam.                    |
| `agent.py`              | Orquestador. Coordina classify → plan → build_messages → recurrence.           |
| `config.py`             | Carga todas las variables de entorno en un `Settings` inmutable.               |
| `models.py`             | Dataclasses de dominio: `TicketFacts`, `AgentAction`, `VerticalPlan`, memoria. |
| `jira_client.py`        | Cliente HTTP para Jira REST API v3. Retorna `JiraTicket` y `JiraBoardContext`. |
| `classifier.py`         | Convierte `JiraTicket` → `TicketFacts`. Resuelve vertical, calcula flags.      |
| `planner.py`            | Decide qué acciones generar por vertical (`VerticalPlan`).                     |
| `message_builder.py`    | Renderiza mensajes de texto para enviar a Roam (verticales + CPO).             |
| `recurrence_analyzer.py`| Llama a Claude API para detectar patrones recurrentes entre tickets.           |
| `memory.py`             | Persiste y carga `AgentMemoryState` desde `data/agent_state.json`.             |
| `roam_client.py`        | Cliente HTTP para Roam API. Envía mensajes por channel ID o webhook.           |

## Capas implícitas

El proyecto no usa un framework con capas explícitas. La separación de responsabilidades es:

```
config.py            → Configuración
models.py            → Modelos de dominio
jira_client.py       → Infraestructura (entrada)
roam_client.py       → Infraestructura (salida)
classifier.py        → Lógica de negocio
planner.py           → Lógica de negocio
message_builder.py   → Lógica de presentación
recurrence_analyzer.py → Análisis IA (opcional)
memory.py            → Persistencia
agent.py             → Orquestación
main.py              → Entry point + wiring
```

La lógica de negocio (`classifier`, `planner`, `message_builder`) no importa clientes ni config directamente — recibe lo que necesita como parámetros.
