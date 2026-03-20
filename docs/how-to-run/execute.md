# Cómo ejecutar el proyecto

## Setup inicial

```bash
# 1. Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con los valores reales
```

Ver [environment-variables.md](../configuration/environment-variables.md) para el detalle de cada variable.

## Ejecución

### Corrida completa (envía mensajes a Roam)

```bash
python src/main.py
```

- Carga settings, memoria, tickets de Jira.
- Clasifica, planifica y construye mensajes.
- Envía a los canales de Roam configurados.
- Persiste el nuevo estado de memoria.

### Dry-run (previsualización sin enviar)

```bash
python src/main.py --dry-run
```

- Ejecuta todo el pipeline normalmente.
- Imprime en stdout el plan y mensaje por vertical.
- Imprime el cuerpo del análisis CPO si aplica.
- **No envía nada a Roam** y **no actualiza la memoria**.

### Listar canales de Roam disponibles

```bash
python src/main.py --list-roam-chats
```

Útil para obtener los IDs de canal a configurar en `ROAM_CHANNEL_IDS_JSON`.

Ejemplo de salida:

```
ID                                                 Tipo       Nombre
------------------------------------------------------------------------------------------
C-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx             C-         payments-alerts
...
```

## Dependencias de entorno

| Dependencia      | Configuración requerida                          |
|------------------|--------------------------------------------------|
| Jira             | `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_BOARD_ID` |
| Roam (API)       | `ROAM_API_TOKEN` + `ROAM_CHANNEL_IDS_JSON`       |
| Roam (webhook)   | `VERTICAL_WEBHOOKS_JSON` o `DEFAULT_ROAM_WEBHOOK` |
| Claude API       | `ANTHROPIC_API_KEY` (opcional, habilita análisis de recurrencia) |

## Archivos generados en runtime

| Archivo                  | Descripción                                    |
|--------------------------|------------------------------------------------|
| `data/agent_state.json`  | Memoria persistida del agente entre corridas.  |

La carpeta `data/` se crea automáticamente en la primera corrida.
