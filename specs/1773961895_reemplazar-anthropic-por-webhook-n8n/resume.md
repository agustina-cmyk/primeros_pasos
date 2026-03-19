**Created at**: 2026-03-19
**Based on plan**: @plan.md
**Based on story**: @story.md

# Resume: Reemplazar cliente Anthropic por webhook n8n para análisis de recurrencia

### Executive Summary
El agente ya no depende del SDK de Anthropic para analizar patrones recurrentes en tickets. Ahora llama a un webhook HTTP genérico (n8n) que recibe `system_prompt` y `user_message`, permitiendo cambiar el modelo o proveedor de IA desde n8n sin tocar el código. Para activarlo, solo hay que configurar `LLM_WEBHOOK_URL` en `.env`.

### Technical Summary
- `src/recurrence_analyzer.py`: eliminado `import anthropic`, reemplazado por `requests.post()` al webhook con `{"system_prompt": ..., "user_message": ...}`
- `src/config.py`: campo `anthropic_api_key` → `llm_webhook_url`, env var `ANTHROPIC_API_KEY` → `LLM_WEBHOOK_URL`
- `src/agent.py` y `src/main.py`: guards y llamadas actualizados al nuevo nombre de campo
- `requirements.txt`: dependencia `anthropic` removida (ya no se usa)
- Comportamiento de fallback conservado: si `LLM_WEBHOOK_URL` está vacío, el análisis se saltea silenciosamente

### Phases Completed
- [x] **Phase 1**: Config y dependencias — renombrado campo en Settings y removido SDK anthropic
- [x] **Phase 2**: Reescribir recurrence_analyzer — HTTP POST al webhook reemplaza llamada al SDK
- [x] **Phase 3**: Actualizar agent.py y main.py — guards y parámetros propagados
