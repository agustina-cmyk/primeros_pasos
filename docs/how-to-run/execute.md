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

### Solo canal CPO (sin notificar verticales)

```bash
python src/main.py --weekly --cpo-only
```

Útil para reenviar el reporte semanal al CPO sin volver a notificar los canales de verticales.

### Forzar corrida semanal

```bash
python src/main.py --weekly
```

Fuerza el reporte CPO semanal y el análisis de roadmap independientemente del día de la semana. Sin este flag, la corrida semanal se activa automáticamente solo los viernes.

### Solo roadmap (sin mensajes a canales)

```bash
python src/main.py --roadmap-only
```

Ejecuta el análisis de roadmap (voto, comentarios, creación de ideas) sin enviar mensajes a los canales de verticales ni al CPO.

### Solo mensajes a canales (sin roadmap)

```bash
python src/main.py --notify-only
```

Envía mensajes a los canales de verticales sin ejecutar el análisis de roadmap. Modo usado por el cron diario.

### Forzar análisis de roadmap

```bash
python src/main.py --force-roadmap
```

Ejecuta el análisis de roadmap aunque no haya cambios detectados en Jira.

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
| LLM webhook      | `LLM_WEBHOOK_URL` (opcional, habilita análisis de recurrencia y roadmap) |

## Archivos generados en runtime

| Archivo                                        | Descripción                                                         |
|------------------------------------------------|---------------------------------------------------------------------|
| `data/agent_state.json`                        | Memoria persistida del agente entre corridas.                       |
| `reports/roadmap_input_<timestamp>.json`       | Input completo enviado al LLM en cada análisis de roadmap.          |
| `reports/recurrence_input_<timestamp>.json`    | Input completo enviado al LLM en cada análisis de recurrencia.      |
| `reports/report_<timestamp>.html`              | Reporte HTML generado en corridas `--dry-run`.                      |

Las carpetas `data/` y `reports/` se crean automáticamente en la primera corrida.
