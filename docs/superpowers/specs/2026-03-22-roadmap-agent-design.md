 p# Diseño: Agente de Representación en Roadmap

**Fecha:** 2026-03-22
**Autor:** Agustina Alvarez (CPO, Vaas)
**Estado:** Aprobado para implementación

---

## Contexto

El agente Vaas actualmente lee tickets del tablero de Production Support en Jira, los clasifica por vertical y notifica a los canales de Roam. Esta extensión le agrega una responsabilidad nueva: actuar como representante del estado de producción dentro de la app de roadmap de Vaas, asegurando que los problemas reales que enfrentan los equipos estén representados en las decisiones de producto.

---

## Objetivo

El agente debe ser capaz de:
1. Leer todas las ideas del roadmap y compararlas con los patrones del tablero de Jira
2. Votar y comentar ideas existentes cuando encuentra relación con problemas reales de producción
3. Crear ideas nuevas (en modo interno) cuando detecta necesidades no representadas
4. Responder consultas en ideas que él mismo creó
5. No hacer nada en el roadmap si no hubo cambios relevantes desde la última corrida

---

## Arquitectura

El diseño divide el trabajo en dos repos:

### Repo `roadmap-app` (cambios mínimos)
Se agregan 5 endpoints REST en `app/api/`, protegidos por JWT de Supabase. El resto de la app no cambia.

### Repo `Proyectos Vaas` (el agente)
Se agregan 2 módulos nuevos (`roadmap_client.py`, `roadmap_analyzer.py`) y se integran al flujo existente de `agent.py`.

---

## Endpoints nuevos en roadmap-app

Todos los endpoints validan el JWT de Supabase en el header `Authorization: Bearer <token>`. Si el token es inválido o está ausente, devuelven `401`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/ideas` | Lista todas las ideas con votos y cantidad de comentarios |
| `GET` | `/api/ideas/[id]/comments` | Lista todos los comentarios de una idea |
| `POST` | `/api/ideas` | Crea una idea con `visibility: internal` |
| `POST` | `/api/ideas/[id]/vote` | Vota positivo o negativo |
| `POST` | `/api/ideas/[id]/comments` | Deja un comentario (o responde uno existente) |

### Payloads y respuestas

**`GET /api/ideas`** — respuesta: array de `RoadmapIdea` (sin cuerpo de comentarios, solo `comment_count`). El cuerpo de los comentarios se obtiene con el endpoint de comments cuando sea necesario.

**`POST /api/ideas`**
```json
{
  "title": "string (requerido)",
  "description": "string (requerido, markdown)",
  "category": "string (requerido, valores válidos: Verification | Payments | Core | Trustee Portal | AI Tracks | Data | Security | UX)"
}
```
Visibility se fija en `internal` server-side. Respuesta: objeto `RoadmapIdea` con `id`.

**`POST /api/ideas/[id]/vote`**
```json
{ "type": "like" | "dislike" }
```
Comportamiento: si el agente ya votó esa idea con el mismo tipo → no hace nada (idempotente). Si votó con tipo distinto → cambia el voto. El endpoint no retorna error si el voto ya existe. El agente puede votar negativamente cuando Claude lo justifica con evidencia de tickets.

**`POST /api/ideas/[id]/comments`**
```json
{
  "body": "string (requerido, markdown)",
  "parent_comment_id": "string (opcional, para responder un comentario existente)"
}
```

### Autenticación del agente
El agente autentica directamente contra Supabase (`signInWithPassword`) usando las credenciales de `ps_agent@getvaas.com`. Esto requiere `ROADMAP_SUPABASE_URL` y `ROADMAP_SUPABASE_ANON_KEY`. El JWT obtenido se usa en el header `Authorization` de cada llamada a los endpoints de `roadmap-app`. El `roadmap-app` no expone endpoint de login propio.

---

## Modelos de datos internos del agente

```python
@dataclass
class RoadmapIdea:
    id: str
    title: str
    description: str
    category: str
    status: str           # draft | submitted | under_review | accepted | rejected | promoted
    visibility: str       # internal | public
    author_email: str
    upvotes: int
    downvotes: int

@dataclass
class RoadmapComment:
    id: str
    body: str
    author_email: str
    idea_id: str
    parent_comment_id: str | None
    created_at: str       # ISO 8601

@dataclass
class NewIdeaData:
    title: str
    description: str      # debe incluir: contexto, pain points, tickets de Jira que lo evidencian, impacto estimado
    category: str

@dataclass
class RoadmapAction:
    action: str           # "vote" | "comment" | "create_idea" | "reply_comment"
    idea_id: str | None
    comment_id: str | None   # solo para "reply_comment"
    vote_type: str | None    # "like" | "dislike"
    comment_body: str | None
    new_idea: NewIdeaData | None

@dataclass
class RoadmapPlan:
    actions: List[RoadmapAction]
    skip_reason: str | None  # si no hay acciones, explica por qué
```

---

## Módulos nuevos en el agente Vaas

### `src/roadmap_client.py`
Responsabilidad única: hablar con la API del roadmap.

```python
def login(supabase_url, anon_key, email, password) -> str
def get_ideas(app_url, token) -> List[RoadmapIdea]
def get_comments(app_url, token, idea_id) -> List[RoadmapComment]
def vote(app_url, token, idea_id, vote_type: str)
def add_comment(app_url, token, idea_id, body, parent_comment_id=None)
def create_idea(app_url, token, data: NewIdeaData) -> RoadmapIdea
```

### `src/roadmap_analyzer.py`
Responsabilidad única: razonar sobre qué acciones tomar en el roadmap. Llama al webhook de n8n configurado en `LLM_WEBHOOK_URL` (mismo que usa `recurrence_analyzer.py`) con system_prompt + user_message, parsea el JSON de respuesta y retorna un `RoadmapPlan`.

**Entrada:**
- Lista de `RecurringPattern` del análisis de recurrencia de Jira
- Lista de `TicketFacts` clasificados (tickets activos del tablero)
- Lista de `RoadmapIdea` actuales
- Memoria previa: `voted_idea_ids`, `commented_idea_ids`, `created_idea_ids`

**Salida:** `RoadmapPlan`

**Límites por corrida:** máximo 5 acciones en total combinadas (votos + comentarios + ideas creadas + respuestas). Si Claude propone más de 5, el agente descarta las sobrantes en orden inverso de prioridad (primero se descartan `create_idea`, luego `comment`, luego `vote`, preservando siempre `reply_comment`).

---

## Flujo completo de una corrida

```
1. El agente corre normalmente:
   Jira → clasificar → planificar → mensajes a Roam por vertical → mensaje CPO

2. Condición de activación del módulo de roadmap:
   Se activa si CUALQUIERA de estas condiciones es verdadera:
   a. Hay tickets nuevos desde la última corrida del agente (created_today=True en TicketFacts)
   b. Hay tickets con cambio de estado desde la última corrida (status_changed=True)
   c. Hay comentarios sin responder en ideas creadas por el agente:
      → para cada idea en created_idea_ids, llama get_comments()
      → un comentario "sin responder" es: author_email != PS_AGENT_EMAIL
        Y su id no está en replied_comment_ids
        Y no es un comment_root (parent_comment_id == None que el agente debería ignorar
        si ya dejó un comentario raíz previo en esa idea)
      → si encuentra al menos uno → activa

   Si ninguna condición aplica → skip completo del módulo de roadmap.

3. Si se activa:
   a. roadmap_client.login() → JWT
   b. roadmap_client.get_ideas() → lista de ideas
   c. Si hay ideas en created_idea_ids → get_comments() por cada una
   d. roadmap_analyzer.analyze() → Claude genera RoadmapPlan
   e. Si plan.actions está vacío → skip con log del skip_reason
   f. Si hay acciones → ejecutarlas en orden (máx 5):
      1. Respuestas a comentarios en ideas propias (reply_comment)
      2. Votos en ideas existentes (vote)
      3. Comentarios en ideas existentes (comment)
      4. Creación de ideas nuevas (create_idea)

4. Si se crearon ideas nuevas:
   → notificar al CPO en el canal de Roam configurado en ROAM_CPO_CHANNEL_ID
     (mismo canal que recibe el mensaje CPO del análisis de recurrencia, vía roam_client existente)
   → formato del mensaje:
     Título: "Nueva idea creada en el roadmap (revisión pendiente)"
     Body: lista de ideas creadas, cada una con:
       - Título de la idea
       - Link directo: construido como f"{ROADMAP_APP_URL}/ideas/{idea.id}"
       - Una línea resumiendo el problema de producción que la motiva

5. CPO entra al roadmap, lee la idea, y si la aprueba cambia visibility a public
```

---

## Memoria extendida

Se agrega una nueva sección `roadmap` a `agent_state.json`:

```json
{
  "roadmap": {
    "last_run_at": "2026-03-22T10:00:00Z",
    "voted_idea_ids": {
      "idea-123": "like",
      "idea-456": "dislike"
    },
    "commented_idea_ids": ["idea-123"],
    "replied_comment_ids": ["comment-789"],
    "created_idea_ids": ["idea-999"]
  }
}
```

`voted_idea_ids` es un dict `id → tipo` para poder detectar cambios de voto en corridas futuras si Claude cambia de opinión. Si Claude propone un voto distinto al ya registrado, el agente ejecuta el cambio y actualiza la memoria.

---

## Variables de entorno nuevas

Agregar al `.env` del agente Vaas:

```
# Credenciales del agente en el roadmap
PS_AGENT_EMAIL=ps_agent@getvaas.com
PS_AGENT_PASSWORD=<contraseña>          ← ya en .env

# Roadmap app
ROADMAP_APP_URL=https://<tu-app>.vercel.app

# Supabase del proyecto roadmap (para login directo)
ROADMAP_SUPABASE_URL=https://<project>.supabase.co
ROADMAP_SUPABASE_ANON_KEY=<anon key>
```

El agente necesita `ROADMAP_SUPABASE_URL` y `ROADMAP_SUPABASE_ANON_KEY` porque el login se hace directamente contra Supabase Auth (no contra `roadmap-app`). `ROADMAP_APP_URL` se usa para llamar a los endpoints REST y para armar los links en las notificaciones de Roam.

---

## Prompt de Claude para el análisis

El webhook de n8n recibe:

```json
{
  "system_prompt": "...",
  "user_message": "..."
}
```

**System prompt:** Claude actúa como representante del equipo de operaciones dentro del roadmap de producto. Su rol es identificar si los problemas recurrentes de producción están siendo considerados en el roadmap y proponer o reforzar ideas con evidencia concreta. Debe ser específico, citar tickets reales, y ser constructivo tanto en votos positivos como negativos. Solo debe proponer acciones donde tenga evidencia clara.

**User message:** incluye:
- Patrones recurrentes detectados en Jira (RecurringPattern list)
- Tickets activos con sus hechos clasificados (TicketFacts, resumidos)
- Lista completa de ideas del roadmap con título, descripción y categoría
- Acciones ya realizadas en corridas anteriores (para no repetir)
- Comentarios sin responder en ideas propias (si los hay)

**Respuesta esperada:** JSON con lista de `RoadmapAction`, máximo 5 items.

---

## Manejo de errores

| Situación | Comportamiento |
|-----------|----------------|
| Login falla | Log de error, skip completo del módulo, agente continúa |
| `get_ideas` falla | Log de error, skip completo del módulo |
| `get_comments` falla para una idea | Log de error, se omite esa idea, se continúa con el resto |
| Claude no devuelve JSON válido | Log de error, skip completo del módulo |
| Plan contiene `idea_id` inexistente | Se omite esa acción, se continúa con las demás |
| Acción desconocida en el plan | Se omite, se loggea como warning |
| Endpoint devuelve error (4xx/5xx) | Log de error, se continúa con la siguiente acción |
| Error en una acción no detiene las demás | Todas las acciones se intentan independientemente |

El módulo de roadmap nunca debe propagar excepciones al flujo principal del agente.

---

## Lo que no hace este agente

- No vota negativamente por defecto — solo cuando Claude detecta que una idea contradice o ignora activamente un problema documentado con evidencia
- No cambia la visibilidad de ideas (eso lo hace el CPO manualmente)
- No elimina ni edita ideas ya publicadas
- No interactúa con el Pipeline — solo con la sección de Ideas
- No ejecuta más de 5 acciones por corrida

---

## Orden de implementación sugerido

1. Endpoints REST en `roadmap-app` + deploy en Vercel
2. Extensión del modelo de memoria en `models.py` (necesario antes de roadmap_client)
3. `roadmap_client.py` en el agente Vaas
4. `roadmap_analyzer.py` con el prompt de Claude
5. Integración en `agent.py` y `main.py`
6. Variables de entorno y documentación (`docs/configuration/environment-variables.md`)
