# AGENTS.md

Agente Python que lee tickets de un board de Jira, los clasifica por vertical de negocio y envía actualizaciones a canales de Roam. Stack: Python 3.13, `requests`, `python-dotenv`, Anthropic Claude API (opcional).

## Comandos clave

| Acción                          | Comando                          |
|---------------------------------|----------------------------------|
| Setup inicial                   | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` |
| Ejecutar el agente              | `python src/main.py`             |
| Dry-run (sin enviar a Roam)     | `python src/main.py --dry-run`   |
| Listar canales de Roam          | `python src/main.py --list-roam-chats` |
| Correr tests                    | `./scripts/run-tests.sh`         |

## Antes de modificar código

Leé la documentación relevante según lo que vas a hacer:

| Qué necesitás entender                          | Leer estos docs                                      |
|-------------------------------------------------|------------------------------------------------------|
| Qué hace cada módulo y cómo se relacionan       | `docs/architecture/project-structure.md`             |
| El flujo completo de datos end-to-end           | `docs/architecture/data-flow.md`                     |
| Reglas de negocio y qué comunica el agente      | `docs/business/agent-decisions.md`                   |
| Terminología de dominio (vertical, stale, etc.) | `docs/business/glossary.md`                          |
| Convenciones de código Python (dataclasses, etc.)| `docs/code/conventions.md`                          |
| Variables de entorno                            | `docs/configuration/environment-variables.md`        |
| Estrategia de testing y qué testear             | `docs/testing/testing-guidelines.md`                 |
| Cómo escribir los tests (nombres, fixtures)     | `docs/testing/test-conventions.md`                   |
| Cómo correr los tests                           | `docs/testing/run-tests.md`                          |

Para identificar qué archivos son relevantes dentro de cada carpeta, los nombres son autodescriptivos.
