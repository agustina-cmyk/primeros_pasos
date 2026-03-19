# Example: Brainstorm

**User prompt:** `/sdd.think cómo podríamos hacer que los skills se puedan versionar independientemente?`

---

**Investigation output:**

## Contexto actual

Hoy todos los skills se sincronizan juntos en `sdd sync` — se borran todos los `sdd.*` y se copian
frescos desde el paquete global. La versión es única en `.sdd.json` y aplica al paquete entero.

Archivos clave:
- `src/commands/sync.ts` — `syncSkills()` copia todo de golpe
- `templates/base/.ai/skills/` — todos los skills viven como directorios estáticos

## Opciones

### Opción 1: Manifest por skill
Agregar un `manifest.json` dentro de cada skill con su versión:
```json
{ "name": "sdd.story", "version": "1.2.0", "minSddVersion": "0.3.0" }
```
`syncSkills()` compararía por skill y solo copiaría los que cambiaron.

**Pros:** Granular, solo actualiza lo necesario, permite rollback por skill.
**Contras:** Más complejidad en sync, hay que mantener versiones por skill, posibles
incompatibilidades entre skills de diferentes versiones.

### Opción 2: Hash-based sync
En vez de versiones, calcular un hash del contenido del skill y comparar.
Solo copiar si el hash difiere.

**Pros:** Automático, no requiere mantener versiones manualmente.
**Contras:** No hay forma de hacer rollback, no comunica qué cambió, misma complejidad
en sync pero sin el beneficio semántico.

### Opción 3: Git submodules para skills
Cada skill como un repo separado, referenciado como submodule.

**Pros:** Versionado completo con git, independencia total.
**Contras:** Enorme complejidad para el usuario, npm install ya no basta,
rompe la simplicidad del modelo actual.

## Recomendación

**Opción 1** es el sweet spot si realmente necesitas esto. Pero antes de implementar,
preguntaría: ¿qué problema concreto estás teniendo? Si es solo que el sync es lento,
el hash-based (opción 2) resuelve eso sin la complejidad del versionado. Si es que necesitas
que usuarios puedan quedarse en una versión vieja de un skill específico, ahí sí la opción 1
tiene sentido.

¿Cuál te interesa explorar más?
