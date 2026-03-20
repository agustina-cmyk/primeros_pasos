**Created at**: 2026-03-19
**Status**: Done
**Based on story**: @story.md

# Plan: Reemplazar cliente Anthropic por webhook n8n para análisis de recurrencia

### Goal
Reemplazar la dependencia del SDK de Anthropic por una llamada HTTP POST a un webhook n8n genérico, pasando `system_prompt` y `user_message` como JSON. El agente queda desacoplado de cualquier proveedor de IA específico.

### Context
- `src/recurrence_analyzer.py` — módulo a reescribir: eliminar `import anthropic`, usar `requests.post()`
- `src/config.py` — renombrar `anthropic_api_key` → `llm_webhook_url`, env var `LLM_WEBHOOK_URL`
- `src/agent.py` — guard `if settings.anthropic_api_key` → `if settings.llm_webhook_url`
- `src/main.py` — guard idéntico en fetch de tickets finalizados
- `requirements.txt` — remover `anthropic`

### Public Contracts
- **Services**:
  - `analyze_recurrence(active_tickets, finalized_tickets, webhook_url: str) -> List[RecurringPattern]`
  - `Settings.llm_webhook_url: str` (env var: `LLM_WEBHOOK_URL`, opcional, default `""`)

### Phases

#### Phase 1: Config y dependencias
Actualizar `config.py` para usar `llm_webhook_url` y limpiar `requirements.txt`.
- [x] En `src/config.py`: renombrar campo `anthropic_api_key` → `llm_webhook_url` en `Settings`
- [x] En `src/config.py`: cambiar `os.getenv("ANTHROPIC_API_KEY", "")` → `os.getenv("LLM_WEBHOOK_URL", "")`
- [x] En `requirements.txt`: remover la línea `anthropic`

#### Phase 2: Reescribir recurrence_analyzer
Reemplazar el cliente Anthropic por HTTP POST al webhook.
- [x] Eliminar `import anthropic`
- [x] Agregar `import requests`
- [x] Cambiar firma de `analyze_recurrence`: `api_key: str` → `webhook_url: str`
- [x] Reemplazar bloque de llamada a Anthropic por `requests.post(webhook_url, json={"system_prompt": ..., "user_message": ...}, timeout=30)`
- [x] Parsear la respuesta del webhook (esperar texto plano o JSON en el body)

#### Phase 3: Actualizar agent.py y main.py
Propagar el cambio de nombre de campo en los guards y llamadas.
- [x] En `src/agent.py`: cambiar `settings.anthropic_api_key` → `settings.llm_webhook_url` (guard + parámetro a `analyze_recurrence`)
- [x] En `src/main.py`: cambiar `settings.anthropic_api_key` → `settings.llm_webhook_url` en el guard de fetch de tickets finalizados

### Next Step
All phases completed. See resume.md.
