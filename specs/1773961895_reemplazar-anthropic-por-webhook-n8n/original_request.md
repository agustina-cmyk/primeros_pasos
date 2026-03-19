en vez de usar el LLM de anthropic, cablear el endpoint con esto:

```
curl --location 'https://n8n.app.getvaas.com/webhook/c0933dd0-864e-4db9-bb65-b003aa8980d2' \
--header 'Content-Type: application/json' \
--data '{
    "system_prompt": "Creame un poema con estilo gotico con el tema que el usuario te diga",
    "user_message": "De gatos"
}'
```

que te permite escribir un system prompt y user message y recibir la respuesta del LLM
