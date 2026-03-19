**Created at**: 2026-03-19
**Status**: Done
**Original input**: @original_request.md
**Plan implemented**: @plan.md

# Story: Reemplazar cliente Anthropic por webhook n8n para análisis de recurrencia

### Description
Actualmente el análisis de recurrencia de tickets llama directamente a la API de Anthropic usando el SDK oficial. Se quiere reemplazar ese mecanismo por un webhook HTTP genérico (n8n) que recibe `system_prompt` y `user_message` como JSON y devuelve la respuesta del LLM, desacoplando el agente de cualquier SDK de IA específico. Esto permite cambiar el modelo o proveedor desde n8n sin tocar el código del agente.

### Acceptance Criteria
- [ ] **Given** que el agente corre, **When** se ejecuta el análisis de recurrencia, **Then** se hace una llamada HTTP POST al webhook con `system_prompt` y `user_message` como JSON
- [ ] **Given** el webhook responde con el texto del LLM, **When** se parsea la respuesta, **Then** se extraen correctamente los `RecurringPattern` como antes
- [ ] **Given** que `ANTHROPIC_API_KEY` está configurada en `.env`, **When** corre el agente, **Then** esa variable ya no se utiliza (puede estar vacía o ausente sin afectar el análisis)
- [ ] **Given** que `LLM_WEBHOOK_URL` está configurada en `.env`, **When** el análisis de recurrencia corre, **Then** usa esa URL como endpoint
- [ ] **Given** que `LLM_WEBHOOK_URL` no está configurada, **When** el análisis de recurrencia intentaría correr, **Then** se saltea silenciosamente (mismo comportamiento que antes sin API key)
- [ ] **Given** que el webhook falla o devuelve error HTTP, **When** ocurre durante el análisis, **Then** el agente loguea un warning y continúa sin interrumpir el flujo principal

### Additional Context
- El webhook acepta `POST` con `Content-Type: application/json` y body `{"system_prompt": "...", "user_message": "..."}`
- La respuesta esperada del webhook es texto plano o JSON con el output del LLM (mismo formato que antes: JSON con lista de patrones)
- La dependencia `anthropic` del SDK puede ser removida de `requirements.txt`
- El campo `anthropic_api_key` en `Settings` puede ser reemplazado por `llm_webhook_url`
