# Example: Basic Plan (text-only, 2 phases)

## Input
- Story: `specs/1772173169_add_testing_preferences_to_sdd_init/story.md`
- Story summary: Add testing preference questions to the `sdd init` skill so generated docs reflect actual team conventions.
- User approved contracts: No code changes (skill text only), no tests needed.
- User approved phases: (1) Modify SKILL.md template, (2) Sync local copy.

## Output

### File: `specs/1772173169_add_testing_preferences_to_sdd_init/plan.md`

```markdown
**Created at**: 2026-02-27
**Status**: Draft
**Based on story**: @specs/1772173169_add_testing_preferences_to_sdd_init/story.md

# Plan: Agregar preguntas de preferencias de testing al skill sdd.init

### Goal
Agregar un paso interactivo al skill `/sdd.init` que pregunte al usuario sus preferencias de testing
antes del discovery, y ajustar los pasos dependientes para que la generacion de documentacion de testing
sea condicional y refleje los requerimientos del usuario.

### Context
- `templates/base/.ai/skills/sdd.init/SKILL.md` — Template del skill sdd.init que se distribuye a los
  usuarios del paquete. Este es el archivo principal a modificar.
- `.ai/skills/sdd.init/SKILL.md` — Copia local sincronizada del template (dogfooding). Debe mantenerse
  identica al template.
- `docs/code/template-system.md` — Explica la distincion entre archivos framework-managed y user-owned.

### Public Contracts
- **Services**: No aplica — no hay cambios en codigo TypeScript.
- **Tests**: No aplica — no hay codigo ejecutable involucrado.

El cambio es exclusivamente en el contenido de texto del SKILL.md (prompt del skill).

### Phases

#### Phase 1: Modificar el SKILL.md template con nuevo paso y ajustes condicionales
Editar `templates/base/.ai/skills/sdd.init/SKILL.md` para incorporar las preferencias de testing.

- [ ] Insertar nuevo paso 4 "Preguntar preferencias de testing" entre paso 3 (legacy code) y paso 4
  (discovery). Usar AskUserQuestion con hasta 3 preguntas.
- [ ] Renumerar todos los pasos siguientes y actualizar referencias internas.
- [ ] Hacer sub-paso 5.4 Testing condicional (omitir si usuario dijo no).
- [ ] Hacer carpeta `testing/` en paso 7 condicional.
- [ ] Agregar excepcion de "testing aspiracional" en paso 8 y en Important Notes.

#### Phase 2: Sincronizar la copia local
Copiar el template actualizado a la copia local para dogfooding.

- [ ] Copiar `templates/base/.ai/skills/sdd.init/SKILL.md` a `.ai/skills/sdd.init/SKILL.md`.
- [ ] Verificar que ambos archivos sean identicos.

### Next Step
Begin with Phase 1: Modificar el SKILL.md template.
```

## Key Observations
- Goal is 1 sentence, aligned with story AC, explains what not how
- Context links only directly relevant files with why each matters
- Public Contracts explicitly states "No aplica" for empty categories instead of omitting silently
- Each phase is a vertical slice — Phase 1 is independently meaningful
- Action items are checkboxes, specific and actionable
- Next Step points to the first phase clearly
- Language matches the user's language (Spanish)
