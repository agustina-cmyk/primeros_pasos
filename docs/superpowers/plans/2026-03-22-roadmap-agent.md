# Roadmap Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender el agente Vaas para que lea el roadmap de producto, vote y comente ideas existentes con evidencia de producción, y cree ideas nuevas (en modo interno) cuando detecta gaps no representados.

**Architecture:** El trabajo se divide en dos repos. Primero se agregan 5 endpoints REST al repo `roadmap-app` (Next.js + Prisma + Supabase). Luego se agregan dos módulos al agente Vaas (`roadmap_client.py` y `roadmap_analyzer.py`) que se integran al flujo existente en `agent.py` y `main.py`.

**Tech Stack:** Python 3.13 + requests (agente Vaas) · Next.js 14 App Router + Prisma + Supabase (roadmap-app) · pytest (tests del agente)

**Spec:** `docs/superpowers/specs/2026-03-22-roadmap-agent-design.md`

---

## Mapa de archivos

### Repo `agustina-cmyk/roadmap-app`

| Archivo | Acción | Responsabilidad |
|---------|--------|-----------------|
| `lib/api-auth.ts` | Crear | Valida Bearer JWT de Supabase para API routes |
| `app/api/ideas/route.ts` | Crear | GET lista ideas · POST crea idea interna |
| `app/api/ideas/[id]/comments/route.ts` | Crear | GET lista comentarios · POST agrega comentario/respuesta |
| `app/api/ideas/[id]/vote/route.ts` | Crear | POST vota like/dislike (idempotente) |

### Repo `Proyectos Vaas`

| Archivo | Acción | Responsabilidad |
|---------|--------|-----------------|
| `scripts/run-tests.sh` | Crear | Script de ejecución de pytest |
| `tests/__init__.py` | Crear | Directorio `tests/` en la raíz del proyecto (mismo nivel que `src/`) |
| `requirements.txt` | Modificar | Agregar pytest, pytest-mock |
| `src/models.py` | Modificar | Agregar dataclasses de roadmap |
| `src/config.py` | Modificar | Agregar settings de roadmap |
| `src/roadmap_client.py` | Crear | HTTP client para la API del roadmap |
| `src/roadmap_analyzer.py` | Crear | Análisis LLM: decide acciones en el roadmap |
| `src/agent.py` | Modificar | Integrar paso de roadmap al flujo |
| `src/main.py` | Modificar | Pasar settings de roadmap a run_agent, manejar notificación CPO |
| `src/memory.py` | Modificar | Serializar/deserializar sección `roadmap` |
| `tests/test_models_roadmap.py` | Crear | Tests de los nuevos dataclasses |
| `tests/test_roadmap_client.py` | Crear | Tests del cliente HTTP (requests mockeados) |
| `tests/test_roadmap_analyzer.py` | Crear | Tests del analizador LLM (webhook mockeado) |

---

## FASE 1: Endpoints en roadmap-app

> Trabajar en el repo `agustina-cmyk/roadmap-app`. Hacer clone local si es necesario.
> Verificar que existen `lib/db/prisma.ts`, `lib/supabase/server.ts`, y `prisma/schema.prisma` antes de empezar.

---

### Task 1: Helper de autenticación para API routes

**Files:**
- Create: `lib/api-auth.ts`

El helper valida el JWT del header `Authorization: Bearer <token>` usando Supabase y retorna el User o lanza 401.

- [ ] **Step 1: Crear `lib/api-auth.ts`**

```typescript
import { createClient } from '@supabase/supabase-js'

export async function getApiUser(request: Request) {
  const authHeader = request.headers.get('Authorization')
  const token = authHeader?.replace('Bearer ', '').trim()
  if (!token) return null

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  const { data: { user }, error } = await supabase.auth.getUser(token)
  if (error || !user) return null
  return user
}

export function unauthorized() {
  return Response.json({ error: 'Unauthorized' }, { status: 401 })
}
```

- [ ] **Step 2: Commit**

```bash
git add lib/api-auth.ts
git commit -m "feat(api): agregar helper de autenticación para API routes"
```

---

### Task 2: GET /api/ideas

**Files:**
- Create: `app/api/ideas/route.ts`

Retorna todas las ideas con conteo de votos y comentarios.

- [ ] **Step 1: Crear `app/api/ideas/route.ts` con el handler GET**

```typescript
import { prisma } from '@/lib/db/prisma'
import { getApiUser, unauthorized } from '@/lib/api-auth'

export async function GET(request: Request) {
  const user = await getApiUser(request)
  if (!user) return unauthorized()

  const ideas = await prisma.idea.findMany({
    include: {
      votes: { select: { type: true } },
      _count: { select: { comments: true } },
    },
    orderBy: { createdAt: 'desc' },
  })

  const result = ideas.map((idea) => ({
    id: idea.id,
    title: idea.title,
    description: idea.description,
    category: idea.category,
    status: idea.status,
    visibility: idea.visibility,
    author_email: idea.authorId,
    upvotes: idea.votes.filter((v) => v.type === 'like').length,
    downvotes: idea.votes.filter((v) => v.type === 'dislike').length,
    comment_count: idea._count.comments,
  }))

  return Response.json(result)
}
```

> Nota: `authorId` en Prisma guarda el ID del User. Si el schema guarda el email directamente, ajustar. Verificar en `prisma/schema.prisma` cómo está definido `authorId` y si hay relación con `User.email`.

- [ ] **Step 2: Commit**

```bash
git add app/api/ideas/route.ts
git commit -m "feat(api): GET /api/ideas — lista ideas para el agente"
```

---

### Task 3: POST /api/ideas

**Files:**
- Modify: `app/api/ideas/route.ts` (agregar handler POST)

Crea una idea con `visibility: internal`. El `authorId` es el ID del usuario autenticado.

- [ ] **Step 1: Agregar handler POST al mismo archivo**

```typescript
import { prisma } from '@/lib/db/prisma'
import { getApiUser, unauthorized } from '@/lib/api-auth'

// ... GET handler existente ...

export async function POST(request: Request) {
  const user = await getApiUser(request)
  if (!user) return unauthorized()

  const body = await request.json()
  const { title, description, category } = body

  if (!title || !description || !category) {
    return Response.json(
      { error: 'title, description y category son requeridos' },
      { status: 400 }
    )
  }

  // Obtener el User de Prisma usando el email de Supabase
  const dbUser = await prisma.user.findUnique({ where: { email: user.email! } })
  if (!dbUser) return Response.json({ error: 'User not found' }, { status: 404 })

  const idea = await prisma.idea.create({
    data: {
      title,
      description,
      category,
      status: 'submitted',
      visibility: 'internal',
      authorId: dbUser.id,
    },
  })

  return Response.json({
    id: idea.id,
    title: idea.title,
    visibility: idea.visibility,
    status: idea.status,
  }, { status: 201 })
}
```

- [ ] **Step 2: Commit**

```bash
git add app/api/ideas/route.ts
git commit -m "feat(api): POST /api/ideas — crear idea interna desde el agente"
```

---

### Task 4: GET y POST /api/ideas/[id]/comments

**Files:**
- Create: `app/api/ideas/[id]/comments/route.ts`

- [ ] **Step 1: Crear el archivo con ambos handlers**

```typescript
import { prisma } from '@/lib/db/prisma'
import { getApiUser, unauthorized } from '@/lib/api-auth'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const user = await getApiUser(request)
  if (!user) return unauthorized()

  const comments = await prisma.comment.findMany({
    where: { entityType: 'idea', entityId: params.id },
    include: { author: { select: { email: true } } },
    orderBy: { createdAt: 'asc' },
  })

  const result = comments.map((c) => ({
    id: c.id,
    body: c.body,
    author_email: c.author.email,
    idea_id: params.id,
    parent_comment_id: c.parentId ?? null,
    created_at: c.createdAt.toISOString(),
  }))

  return Response.json(result)
}

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const user = await getApiUser(request)
  if (!user) return unauthorized()

  const body = await request.json()
  const { body: commentBody, parent_comment_id } = body

  if (!commentBody) {
    return Response.json({ error: 'body es requerido' }, { status: 400 })
  }

  const idea = await prisma.idea.findUnique({ where: { id: params.id } })
  if (!idea) return Response.json({ error: 'Idea not found' }, { status: 404 })

  const dbUser = await prisma.user.findUnique({ where: { email: user.email! } })
  if (!dbUser) return Response.json({ error: 'User not found' }, { status: 404 })

  const comment = await prisma.comment.create({
    data: {
      body: commentBody,
      entityType: 'idea',
      entityId: params.id,
      userId: dbUser.id,
      parentId: parent_comment_id ?? null,
      visibility: 'internal',
    },
  })

  return Response.json({ id: comment.id }, { status: 201 })
}
```

> Verificar en `prisma/schema.prisma` los nombres exactos de campos (`parentId` vs `parent_id`, `userId` vs `authorId`, etc.) y ajustar si difieren.

- [ ] **Step 2: Commit**

```bash
git add "app/api/ideas/[id]/comments/route.ts"
git commit -m "feat(api): GET y POST /api/ideas/[id]/comments"
```

---

### Task 5: POST /api/ideas/[id]/vote

**Files:**
- Create: `app/api/ideas/[id]/vote/route.ts`

Voto idempotente: si ya existe con el mismo tipo no hace nada; si existe con tipo distinto lo actualiza.

- [ ] **Step 1: Crear el archivo**

```typescript
import { prisma } from '@/lib/db/prisma'
import { getApiUser, unauthorized } from '@/lib/api-auth'

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const user = await getApiUser(request)
  if (!user) return unauthorized()

  const body = await request.json()
  const { type } = body

  if (type !== 'like' && type !== 'dislike') {
    return Response.json({ error: 'type debe ser like o dislike' }, { status: 400 })
  }

  const idea = await prisma.idea.findUnique({ where: { id: params.id } })
  if (!idea) return Response.json({ error: 'Idea not found' }, { status: 404 })

  const dbUser = await prisma.user.findUnique({ where: { email: user.email! } })
  if (!dbUser) return Response.json({ error: 'User not found' }, { status: 404 })

  const existing = await prisma.vote.findFirst({
    where: { entityType: 'idea', entityId: params.id, userId: dbUser.id },
  })

  if (existing) {
    if (existing.type === type) {
      // Idempotente: ya existe con el mismo tipo, no hacer nada
      return Response.json({ status: 'no_change' })
    }
    // Cambiar voto
    await prisma.vote.update({ where: { id: existing.id }, data: { type } })
    return Response.json({ status: 'updated' })
  }

  await prisma.vote.create({
    data: { entityType: 'idea', entityId: params.id, userId: dbUser.id, type },
  })
  return Response.json({ status: 'created' }, { status: 201 })
}
```

- [ ] **Step 2: Commit**

```bash
git add "app/api/ideas/[id]/vote/route.ts"
git commit -m "feat(api): POST /api/ideas/[id]/vote — voto idempotente"
```

---

### Task 6: Deploy y smoke test

- [ ] **Step 1: Push y deploy en Vercel**

```bash
git push origin main
```

Vercel despliega automáticamente desde main. Esperar que el deploy termine en el dashboard de Vercel.

- [ ] **Step 2: Smoke test con curl**

Obtener el JWT del agente primero (reemplazar `<SUPABASE_URL>`, `<ANON_KEY>`, `<APP_URL>`):

```bash
# Login → obtener JWT
TOKEN=$(curl -s -X POST \
  "<SUPABASE_URL>/auth/v1/token?grant_type=password" \
  -H "apikey: <ANON_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"email":"ps_agent@getvaas.com","password":"<PASSWORD>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# GET /api/ideas
curl -s -H "Authorization: Bearer $TOKEN" <APP_URL>/api/ideas | python3 -m json.tool | head -30

# POST /api/ideas
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test idea del agente","description":"Test","category":"Core"}' \
  <APP_URL>/api/ideas
```

Resultado esperado: GET retorna array de ideas, POST retorna objeto con `id` y `visibility: "internal"`.

- [ ] **Step 3: Si algo falla, revisar los logs en Vercel dashboard → Functions**

---

## FASE 2: Módulos del agente Vaas

> Trabajar en `/Users/agusalvarez/Documents/Proyectos Vaas`. Activar venv: `source .venv/bin/activate`.

---

### Task 7: Setup de pytest y script de tests

**Files:**
- Modify: `requirements.txt`
- Create: `scripts/run-tests.sh`
- Create: `tests/__init__.py`

- [ ] **Step 1: Agregar pytest y pytest-mock a requirements.txt**

```
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.5
pytest-mock==3.14.0
```

- [ ] **Step 2: Instalar dependencias**

```bash
cd "/Users/agusalvarez/Documents/Proyectos Vaas"
source .venv/bin/activate
pip install pytest==8.3.5 pytest-mock==3.14.0
```

Resultado esperado: `Successfully installed pytest-... pytest-mock-...`

- [ ] **Step 3: Crear `scripts/run-tests.sh`**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
python -m pytest tests/ -v "$@"
```

- [ ] **Step 4: Hacer ejecutable el script**

```bash
chmod +x scripts/run-tests.sh
```

- [ ] **Step 5: Crear `tests/__init__.py`** (archivo vacío) en la raíz del proyecto — es decir, en `tests/`, que es **hermano de `src/`**, no dentro de él.

Estructura resultante:
```
Proyectos Vaas/
├── src/
│   ├── models.py
│   └── ...
├── tests/
│   ├── __init__.py
│   └── (tests van acá)
├── scripts/
│   └── run-tests.sh
└── requirements.txt
```

- [ ] **Step 6: Verificar que pytest corre (sin tests aún)**

```bash
./scripts/run-tests.sh
```

Resultado esperado: `no tests ran` o similar, sin error.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt scripts/run-tests.sh tests/__init__.py
git commit -m "chore: configurar pytest y script de tests"
```

---

### Task 8: Extender models.py con dataclasses de roadmap

**Files:**
- Modify: `src/models.py`
- Create: `tests/test_models_roadmap.py`

- [ ] **Step 1: Escribir el test primero**

Crear `tests/test_models_roadmap.py`:

```python
from models import (
    RoadmapIdea,
    RoadmapComment,
    NewIdeaData,
    RoadmapAction,
    RoadmapPlan,
    RoadmapMemoryState,
    AgentMemoryState,
)


def test_roadmap_idea_fields():
    idea = RoadmapIdea(
        id="abc",
        title="Idea de test",
        description="Descripción",
        category="Core",
        status="submitted",
        visibility="internal",
        author_email="agent@test.com",
        upvotes=2,
        downvotes=0,
        comment_count=1,
    )
    assert idea.id == "abc"
    assert idea.visibility == "internal"


def test_roadmap_action_vote():
    action = RoadmapAction(
        action="vote",
        idea_id="abc",
        comment_id=None,
        vote_type="like",
        comment_body=None,
        new_idea=None,
    )
    assert action.action == "vote"
    assert action.vote_type == "like"


def test_roadmap_plan_empty():
    plan = RoadmapPlan(actions=[], skip_reason="Sin cambios")
    assert plan.actions == []
    assert plan.skip_reason == "Sin cambios"


def test_roadmap_memory_state_defaults():
    state = RoadmapMemoryState()
    assert state.voted_idea_ids == {}
    assert state.commented_idea_ids == []
    assert state.replied_comment_ids == []
    assert state.created_idea_ids == []
    assert state.last_run_at is None


def test_agent_memory_state_includes_roadmap():
    mem = AgentMemoryState.empty()
    assert mem.roadmap is not None
    assert isinstance(mem.roadmap, RoadmapMemoryState)


def test_agent_memory_state_to_dict_includes_roadmap():
    mem = AgentMemoryState.empty()
    mem.roadmap.created_idea_ids.append("idea-1")
    d = mem.to_dict()
    assert "roadmap" in d
    assert d["roadmap"]["created_idea_ids"] == ["idea-1"]
```

- [ ] **Step 2: Correr el test — debe fallar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && source .venv/bin/activate
./scripts/run-tests.sh tests/test_models_roadmap.py -v
```

Resultado esperado: `ImportError` o `ModuleNotFoundError`.

- [ ] **Step 3: Agregar los nuevos dataclasses a `src/models.py`**

Al final del archivo, después de `AgentMemoryState`:

```python
@dataclass(frozen=True)
class RoadmapIdea:
    id: str
    title: str
    description: str
    category: str
    status: str
    visibility: str
    author_email: str
    upvotes: int
    downvotes: int
    comment_count: int


@dataclass(frozen=True)
class RoadmapComment:
    id: str
    body: str
    author_email: str
    idea_id: str
    parent_comment_id: Optional[str]
    created_at: str


@dataclass(frozen=True)
class NewIdeaData:
    title: str
    description: str
    category: str


@dataclass(frozen=True)
class RoadmapAction:
    action: str           # "vote" | "comment" | "create_idea" | "reply_comment"
    idea_id: Optional[str]
    comment_id: Optional[str]
    vote_type: Optional[str]      # "like" | "dislike"
    comment_body: Optional[str]
    new_idea: Optional[NewIdeaData]


@dataclass(frozen=True)
class RoadmapPlan:
    actions: List[RoadmapAction]
    skip_reason: Optional[str]


@dataclass
class RoadmapMemoryState:
    voted_idea_ids: Dict[str, str] = field(default_factory=dict)  # id → "like"|"dislike"
    commented_idea_ids: List[str] = field(default_factory=list)
    replied_comment_ids: List[str] = field(default_factory=list)
    created_idea_ids: List[str] = field(default_factory=list)
    last_run_at: Optional[str] = None
```

Y extender `AgentMemoryState` para incluir `roadmap`. El campo `roadmap` debe ir **después** de `last_run_at` (que ya tiene default) para no romper el ordenamiento de dataclass:

```python
@dataclass
class AgentMemoryState:
    tickets: Dict[str, TicketStateSnapshot]
    last_run_at: Optional[str] = None
    roadmap: RoadmapMemoryState = field(default_factory=RoadmapMemoryState)  # siempre al final

    def to_dict(self) -> Dict[str, object]:
        return {
            "last_run_at": self.last_run_at,
            "tickets": {key: asdict(snapshot) for key, snapshot in self.tickets.items()},
            "roadmap": {
                "last_run_at": self.roadmap.last_run_at,
                "voted_idea_ids": self.roadmap.voted_idea_ids,
                "commented_idea_ids": self.roadmap.commented_idea_ids,
                "replied_comment_ids": self.roadmap.replied_comment_ids,
                "created_idea_ids": self.roadmap.created_idea_ids,
            },
        }

    @classmethod
    def empty(cls) -> "AgentMemoryState":
        return cls(tickets={}, roadmap=RoadmapMemoryState())
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh tests/test_models_roadmap.py -v
```

Resultado esperado: todos los tests en verde.

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models_roadmap.py
git commit -m "feat(models): agregar dataclasses de roadmap y extender AgentMemoryState"
```

---

### Task 9: Extender memory.py para deserializar la sección roadmap

**Files:**
- Modify: `src/memory.py`

- [ ] **Step 1: Actualizar el método `load()` en `src/memory.py`**

Agregar la deserialización de la sección `roadmap` al leer el JSON:

```python
from models import AgentMemoryState, RoadmapMemoryState, TicketStateSnapshot

# En el método load(), después de construir `tickets`:

roadmap_raw = data.get("roadmap", {})
roadmap = RoadmapMemoryState(
    voted_idea_ids=roadmap_raw.get("voted_idea_ids", {}),
    commented_idea_ids=roadmap_raw.get("commented_idea_ids", []),
    replied_comment_ids=roadmap_raw.get("replied_comment_ids", []),
    created_idea_ids=roadmap_raw.get("created_idea_ids", []),
    last_run_at=roadmap_raw.get("last_run_at"),
)

return AgentMemoryState(
    tickets=tickets,
    last_run_at=data.get("last_run_at"),
    roadmap=roadmap,
)
```

- [ ] **Step 2: Correr los tests existentes para verificar que no se rompió nada**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh -v
```

Resultado esperado: todos en verde.

- [ ] **Step 3: Commit**

```bash
git add src/memory.py
git commit -m "feat(memory): deserializar sección roadmap en AgentMemoryState"
```

---

### Task 10: Extender config.py con settings de roadmap

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Agregar campos al dataclass `Settings`**

```python
# Al final de los campos del dataclass Settings:
roadmap_app_url: str
roadmap_supabase_url: str
roadmap_supabase_anon_key: str
ps_agent_email: str
ps_agent_password: str
```

- [ ] **Step 2: Agregar la carga de esos campos en `load_settings()`**

```python
return Settings(
    # ... campos existentes ...
    roadmap_app_url=os.getenv("ROADMAP_APP_URL", "").strip(),
    roadmap_supabase_url=os.getenv("ROADMAP_SUPABASE_URL", "").strip(),
    roadmap_supabase_anon_key=os.getenv("ROADMAP_SUPABASE_ANON_KEY", "").strip(),
    ps_agent_email=os.getenv("PS_AGENT_EMAIL", "").strip(),
    ps_agent_password=os.getenv("PS_AGENT_PASSWORD", "").strip(),
)
```

Los campos son opcionales (default vacío): si no están configurados, el módulo de roadmap se saltea silenciosamente.

- [ ] **Step 3: Correr los tests**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh -v
```

- [ ] **Step 4: Commit**

```bash
git add src/config.py
git commit -m "feat(config): agregar settings de roadmap (opcionales)"
```

---

### Task 11: Implementar roadmap_client.py

**Files:**
- Create: `src/roadmap_client.py`
- Create: `tests/test_roadmap_client.py`

- [ ] **Step 1: Escribir los tests primero**

Crear `tests/test_roadmap_client.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from models import NewIdeaData


@pytest.fixture
def mock_login_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"access_token": "test-jwt-token"}
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def mock_ideas_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = [
        {
            "id": "idea-1",
            "title": "Idea de prueba",
            "description": "Descripción",
            "category": "Core",
            "status": "submitted",
            "visibility": "public",
            "author_email": "user@test.com",
            "upvotes": 3,
            "downvotes": 1,
            "comment_count": 2,
        }
    ]
    mock.raise_for_status = MagicMock()
    return mock


def test_login_returns_token(mock_login_response):
    with patch("roadmap_client.requests.post", return_value=mock_login_response):
        import roadmap_client
        token = roadmap_client.login(
            supabase_url="https://test.supabase.co",
            anon_key="anon-key",
            email="agent@test.com",
            password="pass",
        )
    assert token == "test-jwt-token"


def test_get_ideas_returns_list(mock_ideas_response):
    with patch("roadmap_client.requests.get", return_value=mock_ideas_response):
        import roadmap_client
        ideas = roadmap_client.get_ideas(
            app_url="https://app.vercel.app",
            token="test-jwt",
        )
    assert len(ideas) == 1
    assert ideas[0].id == "idea-1"
    assert ideas[0].upvotes == 3


def test_vote_calls_correct_endpoint():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("roadmap_client.requests.post", return_value=mock_resp) as mock_post:
        import roadmap_client
        roadmap_client.vote(
            app_url="https://app.vercel.app",
            token="test-jwt",
            idea_id="idea-1",
            vote_type="like",
        )
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "idea-1/vote" in call_args[0][0]
    assert call_args[1]["json"]["type"] == "like"


def test_add_comment_calls_correct_endpoint():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("roadmap_client.requests.post", return_value=mock_resp) as mock_post:
        import roadmap_client
        roadmap_client.add_comment(
            app_url="https://app.vercel.app",
            token="test-jwt",
            idea_id="idea-1",
            body="Comentario de prueba",
        )
    call_args = mock_post.call_args
    assert "idea-1/comments" in call_args[0][0]
    assert call_args[1]["json"]["body"] == "Comentario de prueba"
    assert "parent_comment_id" not in call_args[1]["json"] or call_args[1]["json"]["parent_comment_id"] is None


def test_create_idea_returns_roadmap_idea():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "id": "new-idea-1",
        "title": "Nueva idea",
        "visibility": "internal",
        "status": "submitted",
    }
    with patch("roadmap_client.requests.post", return_value=mock_resp):
        import roadmap_client
        idea = roadmap_client.create_idea(
            app_url="https://app.vercel.app",
            token="test-jwt",
            data=NewIdeaData(title="Nueva idea", description="Desc", category="Core"),
        )
    assert idea["id"] == "new-idea-1"
    assert idea["visibility"] == "internal"
```

- [ ] **Step 2: Correr los tests — deben fallar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh tests/test_roadmap_client.py -v
```

Resultado esperado: `ModuleNotFoundError: roadmap_client`.

- [ ] **Step 3: Crear `src/roadmap_client.py`**

```python
from dataclasses import asdict
from typing import Dict, List, Optional

import requests

from models import NewIdeaData, RoadmapComment, RoadmapIdea


def login(supabase_url: str, anon_key: str, email: str, password: str) -> str:
    response = requests.post(
        f"{supabase_url}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_ideas(app_url: str, token: str) -> List[RoadmapIdea]:
    response = requests.get(
        f"{app_url}/api/ideas",
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return [
        RoadmapIdea(
            id=item["id"],
            title=item["title"],
            description=item.get("description", ""),
            category=item.get("category", ""),
            status=item.get("status", ""),
            visibility=item.get("visibility", ""),
            author_email=item.get("author_email", ""),
            upvotes=item.get("upvotes", 0),
            downvotes=item.get("downvotes", 0),
            comment_count=item.get("comment_count", 0),
        )
        for item in response.json()
    ]


def get_comments(app_url: str, token: str, idea_id: str) -> List[RoadmapComment]:
    response = requests.get(
        f"{app_url}/api/ideas/{idea_id}/comments",
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return [
        RoadmapComment(
            id=item["id"],
            body=item["body"],
            author_email=item.get("author_email", ""),
            idea_id=idea_id,
            parent_comment_id=item.get("parent_comment_id"),
            created_at=item.get("created_at", ""),
        )
        for item in response.json()
    ]


def vote(app_url: str, token: str, idea_id: str, vote_type: str) -> None:
    response = requests.post(
        f"{app_url}/api/ideas/{idea_id}/vote",
        json={"type": vote_type},
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()


def add_comment(
    app_url: str,
    token: str,
    idea_id: str,
    body: str,
    parent_comment_id: Optional[str] = None,
) -> None:
    payload: Dict = {"body": body}
    if parent_comment_id:
        payload["parent_comment_id"] = parent_comment_id
    response = requests.post(
        f"{app_url}/api/ideas/{idea_id}/comments",
        json=payload,
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()


def create_idea(app_url: str, token: str, data: NewIdeaData) -> Dict:
    response = requests.post(
        f"{app_url}/api/ideas",
        json={"title": data.title, "description": data.description, "category": data.category},
        headers=_auth_headers(token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh tests/test_roadmap_client.py -v
```

Resultado esperado: todos en verde.

- [ ] **Step 5: Commit**

```bash
git add src/roadmap_client.py tests/test_roadmap_client.py
git commit -m "feat(roadmap): agregar roadmap_client con tests"
```

---

### Task 12: Implementar roadmap_analyzer.py

**Files:**
- Create: `src/roadmap_analyzer.py`
- Create: `tests/test_roadmap_analyzer.py`

- [ ] **Step 1: Escribir los tests primero**

Crear `tests/test_roadmap_analyzer.py`:

```python
import json
from unittest.mock import MagicMock, patch

import pytest

from models import NewIdeaData, RoadmapAction, RoadmapIdea, RoadmapMemoryState


def _make_idea(id="idea-1", title="Test idea", category="Core"):
    return RoadmapIdea(
        id=id, title=title, description="Desc", category=category,
        status="submitted", visibility="public", author_email="other@test.com",
        upvotes=1, downvotes=0, comment_count=0,
    )


def _mock_webhook_response(actions):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"response": json.dumps(actions)}
    return mock


def test_analyze_returns_vote_action():
    actions_json = [{"action": "vote", "idea_id": "idea-1", "vote_type": "like",
                     "comment_body": "Evidencia de PS-123", "comment_id": None, "new_idea": None}]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert len(plan.actions) == 1
    assert plan.actions[0].action == "vote"
    assert plan.actions[0].vote_type == "like"


def test_analyze_returns_create_idea_action():
    new_idea = {"title": "Nueva idea", "description": "Pain points...", "category": "Core"}
    actions_json = [{"action": "create_idea", "idea_id": None, "vote_type": None,
                     "comment_body": None, "comment_id": None, "new_idea": new_idea}]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert plan.actions[0].action == "create_idea"
    assert plan.actions[0].new_idea.title == "Nueva idea"


def test_analyze_caps_at_five_actions():
    actions_json = [
        {"action": "vote", "idea_id": f"idea-{i}", "vote_type": "like",
         "comment_body": None, "comment_id": None, "new_idea": None}
        for i in range(8)
    ]
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response(actions_json)):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea(id=f"idea-{i}") for i in range(8)],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert len(plan.actions) <= 5


def test_analyze_returns_skip_on_empty_response():
    with patch("roadmap_analyzer.requests.post", return_value=_mock_webhook_response([])):
        from roadmap_analyzer import analyze_roadmap
        plan = analyze_roadmap(
            active_tickets=[],
            recurring_patterns=[],
            ideas=[_make_idea()],
            roadmap_memory=RoadmapMemoryState(),
            webhook_url="https://n8n.test/webhook",
        )
    assert plan.actions == []
    assert plan.skip_reason is not None


def test_analyze_raises_on_invalid_json():
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"response": "esto no es json válido {{{"}
    with patch("roadmap_analyzer.requests.post", return_value=mock):
        from roadmap_analyzer import analyze_roadmap
        with pytest.raises(ValueError, match="JSON"):
            analyze_roadmap(
                active_tickets=[],
                recurring_patterns=[],
                ideas=[_make_idea()],
                roadmap_memory=RoadmapMemoryState(),
                webhook_url="https://n8n.test/webhook",
            )
```

- [ ] **Step 2: Correr los tests — deben fallar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh tests/test_roadmap_analyzer.py -v
```

Resultado esperado: `ModuleNotFoundError: roadmap_analyzer`.

- [ ] **Step 3: Crear `src/roadmap_analyzer.py`**

```python
import json
from typing import List

import requests

from jira_client import JiraTicket
from models import (
    NewIdeaData,
    RoadmapAction,
    RoadmapIdea,
    RoadmapMemoryState,
    RoadmapPlan,
)
from recurrence_analyzer import RecurringPattern

_MAX_ACTIONS = 5
_ACTION_PRIORITY = ["reply_comment", "vote", "comment", "create_idea"]

_SYSTEM_PROMPT = """Sos un representante del equipo de operaciones dentro del roadmap de producto de Vaas.
Tu tarea es analizar los problemas recurrentes del tablero de Production Support y determinar acciones concretas en el roadmap.

Reglas:
- Solo proponés acciones cuando tenés evidencia clara de tickets reales.
- Votás positivamente ideas que resuelven problemas documentados en Jira.
- Votás negativamente solo si una idea contradice activamente un problema conocido.
- Creás ideas nuevas (create_idea) solo cuando no existe ninguna idea relacionada.
- Para reply_comment: respondés preguntas en ideas que vos creaste, con contexto de los tickets originales.
- Máximo 5 acciones en total.

Respondé ÚNICAMENTE con un JSON válido (sin texto adicional):
[
  {
    "action": "vote" | "comment" | "create_idea" | "reply_comment",
    "idea_id": "string o null",
    "comment_id": "string o null (solo para reply_comment)",
    "vote_type": "like" | "dislike" | null,
    "comment_body": "string o null",
    "new_idea": {"title": "...", "description": "...", "category": "..."} | null
  }
]

Si no hay acciones necesarias, retorná: []"""


def analyze_roadmap(
    active_tickets: List[JiraTicket],
    recurring_patterns: List[RecurringPattern],
    ideas: List[RoadmapIdea],
    roadmap_memory: RoadmapMemoryState,
    webhook_url: str,
) -> RoadmapPlan:
    ticket_summaries = [
        {"key": t.key, "summary": t.summary, "status": t.status,
         "description": t.description[:200] if t.description else ""}
        for t in active_tickets
    ]
    pattern_summaries = [
        {"label": p.label, "ticket_keys": p.ticket_keys, "recommendation": p.recommendation}
        for p in recurring_patterns
    ]
    idea_summaries = [
        {"id": i.id, "title": i.title, "description": i.description[:200],
         "category": i.category, "upvotes": i.upvotes}
        for i in ideas
    ]

    user_message = (
        f"Tickets activos en Production Support:\n{json.dumps(ticket_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Patrones recurrentes detectados:\n{json.dumps(pattern_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Ideas actuales en el roadmap:\n{json.dumps(idea_summaries, ensure_ascii=False, indent=2)}\n\n"
        f"Acciones ya realizadas por el agente (no repetir):\n"
        f"- Votadas: {list(roadmap_memory.voted_idea_ids.keys())}\n"
        f"- Comentadas: {roadmap_memory.commented_idea_ids}\n"
        f"- Ideas creadas: {roadmap_memory.created_idea_ids}"
    )

    response = requests.post(
        webhook_url,
        json={"system_prompt": _SYSTEM_PROMPT, "user_message": user_message},
        timeout=120,
    )
    response.raise_for_status()

    body = response.json()
    raw = (body.get("response") if isinstance(body, dict) else response.text).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"roadmap_analyzer: JSON inválido en respuesta del webhook: {exc}") from exc

    if not items:
        return RoadmapPlan(actions=[], skip_reason="Claude no detectó acciones necesarias")

    actions = []
    for item in items:
        new_idea_data = None
        if item.get("new_idea"):
            ni = item["new_idea"]
            new_idea_data = NewIdeaData(
                title=ni.get("title", ""),
                description=ni.get("description", ""),
                category=ni.get("category", ""),
            )
        actions.append(RoadmapAction(
            action=item.get("action", ""),
            idea_id=item.get("idea_id"),
            comment_id=item.get("comment_id"),
            vote_type=item.get("vote_type"),
            comment_body=item.get("comment_body"),
            new_idea=new_idea_data,
        ))

    # Aplicar cap de 5 acciones: se preservan por prioridad
    if len(actions) > _MAX_ACTIONS:
        actions = _apply_cap(actions)

    return RoadmapPlan(actions=actions, skip_reason=None)


def _apply_cap(actions: List[RoadmapAction]) -> List[RoadmapAction]:
    """Mantiene máximo _MAX_ACTIONS acciones, preservando por prioridad."""
    ordered = sorted(actions, key=lambda a: _ACTION_PRIORITY.index(a.action)
                     if a.action in _ACTION_PRIORITY else len(_ACTION_PRIORITY))
    return ordered[:_MAX_ACTIONS]
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh tests/test_roadmap_analyzer.py -v
```

Resultado esperado: todos en verde.

- [ ] **Step 5: Commit**

```bash
git add src/roadmap_analyzer.py tests/test_roadmap_analyzer.py
git commit -m "feat(roadmap): agregar roadmap_analyzer con tests"
```

---

### Task 13: Integrar el módulo de roadmap en agent.py

**Files:**
- Modify: `src/agent.py`

La función `run_agent` recibe el resultado del análisis de roadmap como parte de su output. El agente no ejecuta las acciones (eso lo hace `main.py`), solo determina el plan.

- [ ] **Step 1: Actualizar la firma y el return de `run_agent` en `src/agent.py`**

```python
from typing import Dict, List, Optional, Tuple

from classifier import build_next_memory_state, classify_tickets
from config import Settings
from jira_client import JiraBoardContext, JiraTicket
from message_builder import build_cpo_message, build_vertical_message
from models import AgentMemoryState, RoadmapPlan, VerticalPlan
from planner import build_vertical_plan


def run_agent(
    settings: Settings,
    tickets: List[JiraTicket],
    finalized_tickets: List[JiraTicket],
    board_context: JiraBoardContext | None,
    memory_state: AgentMemoryState,
) -> Tuple[Dict[str, VerticalPlan], List[Tuple[str, str, str]], Optional[str], AgentMemoryState, Optional[RoadmapPlan]]:
    grouped_facts = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        stale_ticket_days=settings.stale_ticket_days,
    )

    project_label = _project_label(settings.jira_board_id, board_context)
    plans: Dict[str, VerticalPlan] = {}
    outbound_messages: List[Tuple[str, str, str]] = []

    for vertical, facts in grouped_facts.items():
        plan = build_vertical_plan(vertical=vertical, tickets=facts)
        plans[vertical] = plan
        if not plan.actions:
            continue

        title, body = build_vertical_message(
            project_label=project_label,
            plan=plan,
            channel_url=settings.roam_channel_urls.get(vertical, ""),
            max_items=settings.max_items_per_vertical,
            last_run_at=memory_state.last_run_at,
        )
        outbound_messages.append((vertical, title, body))

    recurring_patterns = None
    if settings.llm_webhook_url:
        try:
            from recurrence_analyzer import analyze_recurrence
            recurring_patterns = analyze_recurrence(
                active_tickets=tickets,
                finalized_tickets=finalized_tickets,
                webhook_url=settings.llm_webhook_url,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de recurrencia falló: {exc}")

    cpo_body = build_cpo_message(
        project_label=project_label,
        grouped_facts=grouped_facts,
        recurring_patterns=recurring_patterns,
    )

    # Análisis de roadmap (opcional)
    roadmap_plan = None
    if _should_run_roadmap(settings, tickets, memory_state):
        try:
            roadmap_plan = _run_roadmap_analysis(
                settings=settings,
                tickets=tickets,
                recurring_patterns=recurring_patterns or [],
                memory_state=memory_state,
            )
        except Exception as exc:
            print(f"[WARN] Análisis de roadmap falló: {exc}")

    next_memory = build_next_memory_state(grouped_facts)
    # Preservar la sección roadmap existente para que main.py la actualice
    next_memory.roadmap = memory_state.roadmap

    return plans, outbound_messages, cpo_body, next_memory, roadmap_plan


def _should_run_roadmap(settings: Settings, tickets: List[JiraTicket], memory_state: AgentMemoryState) -> bool:
    """Activa el módulo de roadmap si hay cambios relevantes."""
    if not settings.roadmap_app_url or not settings.ps_agent_email:
        return False

    from classifier import classify_tickets
    # Verificar si hay tickets nuevos o con cambio de estado
    grouped = classify_tickets(
        tickets=tickets,
        memory_state=memory_state,
        label_prefix=settings.vertical_label_prefix,
        label_to_vertical=settings.label_to_vertical,
        stale_ticket_days=settings.stale_ticket_days,
    )
    all_facts = [f for facts in grouped.values() for f in facts]
    has_changes = any(f.created_today or f.status_changed for f in all_facts)

    # Verificar si hay comentarios sin responder en ideas propias
    has_pending_comments = False
    if memory_state.roadmap.created_idea_ids:
        try:
            import roadmap_client
            token = roadmap_client.login(
                supabase_url=settings.roadmap_supabase_url,
                anon_key=settings.roadmap_supabase_anon_key,
                email=settings.ps_agent_email,
                password=settings.ps_agent_password,
            )
            for idea_id in memory_state.roadmap.created_idea_ids:
                comments = roadmap_client.get_comments(settings.roadmap_app_url, token, idea_id)
                for c in comments:
                    if (c.author_email != settings.ps_agent_email
                            and c.id not in memory_state.roadmap.replied_comment_ids):
                        has_pending_comments = True
                        break
        except Exception as exc:
            print(f"[WARN] No se pudieron verificar comentarios pendientes: {exc}")

    return has_changes or has_pending_comments


def _run_roadmap_analysis(settings, tickets, recurring_patterns, memory_state):
    import roadmap_client
    from roadmap_analyzer import analyze_roadmap

    token = roadmap_client.login(
        supabase_url=settings.roadmap_supabase_url,
        anon_key=settings.roadmap_supabase_anon_key,
        email=settings.ps_agent_email,
        password=settings.ps_agent_password,
    )
    ideas = roadmap_client.get_ideas(settings.roadmap_app_url, token)
    return analyze_roadmap(
        active_tickets=tickets,
        recurring_patterns=recurring_patterns,
        ideas=ideas,
        roadmap_memory=memory_state.roadmap,
        webhook_url=settings.llm_webhook_url,
    )


def _project_label(board_id: str, board_context: JiraBoardContext | None) -> str:
    if board_context is None:
        return f"Board {board_id}"
    return board_context.project_name or board_context.project_key or board_context.board_name
```

- [ ] **Step 2: Correr todos los tests**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh -v
```

Resultado esperado: todos en verde.

- [ ] **Step 3: Commit**

```bash
git add src/agent.py
git commit -m "feat(agent): integrar análisis de roadmap al flujo del agente"
```

---

### Task 14: Integrar en main.py — ejecutar acciones y notificar CPO

> ⚠️ **IMPORTANTE:** Task 13 cambió `run_agent()` para retornar una 5-tupla. Antes de correr el agente, **el primer paso de esta task es actualizar el unpack** en `main.py`, o el agente fallará con `ValueError: too many values to unpack`.

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Actualizar el unpack de `run_agent` en `main.py` (línea ~54)**

Cambiar:
```python
plans, outbound_messages, cpo_body, next_memory = run_agent(...)
```
Por:
```python
plans, outbound_messages, cpo_body, next_memory, roadmap_plan = run_agent(...)
```

- [ ] **Step 2: Agregar la ejecución de acciones del roadmap**

En la función `run()`, después del unpack:

```python
plans, outbound_messages, cpo_body, next_memory, roadmap_plan = run_agent(
    settings=settings,
    tickets=tickets,
    finalized_tickets=finalized_tickets,
    board_context=board_context,
    memory_state=memory_state,
)
```

- [ ] **Step 3: Agregar la ejecución del plan de roadmap antes de `memory.save(next_memory)`**

```python
# Ejecutar acciones del roadmap
if roadmap_plan and roadmap_plan.actions:
    created_ideas = _execute_roadmap_plan(settings, roadmap_plan, next_memory)
    if created_ideas and not dry_run:
        _notify_cpo_roadmap(settings, roam, created_ideas)
```

- [ ] **Step 2: Agregar las funciones `_execute_roadmap_plan` y `_notify_cpo_roadmap` al final de `main.py`**

```python
def _execute_roadmap_plan(settings, roadmap_plan, next_memory):
    """Ejecuta las acciones del plan de roadmap y actualiza la memoria."""
    import roadmap_client

    try:
        token = roadmap_client.login(
            supabase_url=settings.roadmap_supabase_url,
            anon_key=settings.roadmap_supabase_anon_key,
            email=settings.ps_agent_email,
            password=settings.ps_agent_password,
        )
    except Exception as exc:
        print(f"[WARN] Roadmap login falló al ejecutar plan: {exc}")
        return []

    created_ideas = []

    for action in roadmap_plan.actions:
        try:
            if action.action == "vote" and action.idea_id:
                roadmap_client.vote(settings.roadmap_app_url, token, action.idea_id, action.vote_type)
                next_memory.roadmap.voted_idea_ids[action.idea_id] = action.vote_type
                print(f"[ROADMAP] Voto '{action.vote_type}' en idea {action.idea_id}")

            elif action.action == "comment" and action.idea_id and action.comment_body:
                roadmap_client.add_comment(settings.roadmap_app_url, token, action.idea_id, action.comment_body)
                if action.idea_id not in next_memory.roadmap.commented_idea_ids:
                    next_memory.roadmap.commented_idea_ids.append(action.idea_id)
                print(f"[ROADMAP] Comentario en idea {action.idea_id}")

            elif action.action == "reply_comment" and action.idea_id and action.comment_id and action.comment_body:
                roadmap_client.add_comment(
                    settings.roadmap_app_url, token, action.idea_id,
                    action.comment_body, parent_comment_id=action.comment_id,
                )
                next_memory.roadmap.replied_comment_ids.append(action.comment_id)
                print(f"[ROADMAP] Respuesta al comentario {action.comment_id}")

            elif action.action == "create_idea" and action.new_idea:
                result = roadmap_client.create_idea(settings.roadmap_app_url, token, action.new_idea)
                idea_id = result["id"]
                next_memory.roadmap.created_idea_ids.append(idea_id)
                created_ideas.append({"id": idea_id, "title": action.new_idea.title})
                print(f"[ROADMAP] Idea creada: {idea_id} — {action.new_idea.title}")

        except Exception as exc:
            print(f"[WARN] Acción de roadmap falló ({action.action}): {exc}")

    return created_ideas


def _notify_cpo_roadmap(settings, roam, created_ideas):
    """Notifica al CPO sobre ideas creadas en el roadmap."""
    if not settings.roam_cpo_channel_id or not created_ideas:
        return
    lines = ["Nueva idea creada en el roadmap (revisión pendiente)\n"]
    for idea in created_ideas:
        link = f"{settings.roadmap_app_url}/ideas/{idea['id']}"
        lines.append(f"• [{idea['title']}]({link})")
    message = "\n".join(lines)
    try:
        roam.post_message(chat_id=settings.roam_cpo_channel_id, text=message)
        print(f"[ROADMAP] CPO notificado sobre {len(created_ideas)} idea(s) nueva(s).")
    except Exception as exc:
        print(f"[WARN] No se pudo notificar al CPO sobre ideas nuevas: {exc}")
```

- [ ] **Step 3: Correr todos los tests**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas && ./scripts/run-tests.sh -v
```

Resultado esperado: todos en verde.

- [ ] **Step 4: Probar en dry-run (requiere tener .env configurado)**

```bash
cd /Users/agusalvarez/Documents/Proyectos\ Vaas
source .venv/bin/activate
python src/main.py --dry-run
```

Verificar que el agente corre sin errores. Si `ROADMAP_APP_URL` no está configurado, el módulo de roadmap se saltea silenciosamente.

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "feat(main): ejecutar acciones de roadmap y notificar al CPO"
```

---

### Task 15: Variables de entorno y documentación

**Files:**
- Modify: `.env` (agregar las vars faltantes)
- Modify: `docs/configuration/environment-variables.md`

- [ ] **Step 1: Agregar las variables al `.env`**

```
# Roadmap agent
ROADMAP_APP_URL=https://<tu-app>.vercel.app
ROADMAP_SUPABASE_URL=https://<project-id>.supabase.co
ROADMAP_SUPABASE_ANON_KEY=<anon-key>
```

`PS_AGENT_EMAIL` y `PS_AGENT_PASSWORD` ya están en `.env`.

Para obtener `ROADMAP_SUPABASE_URL` y `ROADMAP_SUPABASE_ANON_KEY`: ir al dashboard de Supabase del proyecto roadmap → Settings → API.

- [ ] **Step 2: Correr el agente con --dry-run para verificar el flujo completo**

```bash
python src/main.py --dry-run
```

Resultado esperado: el agente corre normalmente. Si hay tickets con cambios, se activa el módulo de roadmap y aparece `[ROADMAP] ...` en el output.

- [ ] **Step 3: Actualizar `docs/configuration/environment-variables.md`** con las nuevas variables

- [ ] **Step 4: Commit final**

```bash
git add docs/configuration/environment-variables.md
git commit -m "docs: documentar variables de entorno del módulo de roadmap"
```

---

## Resumen de commits esperados

```
chore: configurar pytest y script de tests
feat(models): agregar dataclasses de roadmap y extender AgentMemoryState
feat(memory): deserializar sección roadmap en AgentMemoryState
feat(config): agregar settings de roadmap (opcionales)
feat(roadmap): agregar roadmap_client con tests
feat(roadmap): agregar roadmap_analyzer con tests
feat(agent): integrar análisis de roadmap al flujo del agente
feat(main): ejecutar acciones de roadmap y notificar al CPO
docs: documentar variables de entorno del módulo de roadmap
```
