# Example: Multi-phase Plan (code changes, 3 phases)

## Input
- Story: `specs/1773200755_replace_claude_symlinks_with_rules/story.md`
- Story summary: Replace AGENTS.md→CLAUDE.md symlinks with a `.claude/rules/` file managed as a framework template.
- User approved contracts: Modified functions in init.ts and update.ts, modified shell script, new template file.
- User approved phases: (1) Template + Init, (2) Clean script, (3) Update path.

## Output

### File: `specs/1773200755_replace_claude_symlinks_with_rules/plan.md`

```markdown
**Created at**: 2026-03-11
**Status**: Draft
**Based on story**: @specs/1773200755_replace_claude_symlinks_with_rules/story.md

# Plan: Reemplazar symlinks AGENTS.md→CLAUDE.md con regla en .claude/rules/

### Goal
Eliminar la creación de symlinks `CLAUDE.md → AGENTS.md` del flujo de setup de Claude Code y
reemplazarla con un único archivo de regla `.claude/rules/agents-context.md` que se gestiona como
template framework-managed. Esto elimina problemas de portabilidad cross-platform y mantenimiento manual.

### Context
- `src/commands/init.ts` — Comando init; contiene `setupClaudeCode()` que ejecuta el script de symlinks.
  Se modificará para también copiar la regla a `.claude/rules/`.
- `src/commands/update.ts` — Comando update; gestiona paths framework-managed. Se extenderá para
  actualizar `.claude/rules/agents-context.md`.
- `templates/base/.ai/scripts/claude-code/create-symlinks.sh` — Script que crea symlinks. Se eliminará
  la sección de AGENTS.md.
- `src/utils/fs.ts` — Utilidad `copyDirRecursive()` usada para copiar templates.

### Public Contracts
- **Funciones modificadas**:
  - `setupClaudeCode(projectRoot: string): void` en `init.ts` — se agrega creación de
    `.claude/rules/agents-context.md` copiándolo desde templates.
  - `execute(_args: string[]): Promise<void>` en `update.ts` — si existe `.claude/`, se actualiza
    `agents-context.md` con la versión del template.
- **Script modificado**:
  - `create-symlinks.sh` — se elimina Part 1 (symlinks AGENTS.md). Se mantiene Part 2 (skills).
- **Nuevo archivo template**:
  - `templates/base/.ai/scripts/claude-code/rules/agents-context.md`

### Phases

#### Phase 1: Template + Init
Crear el archivo de regla como template y modificar init para copiarlo a `.claude/rules/`.

- [ ] Crear directorio `templates/base/.ai/scripts/claude-code/rules/`
- [ ] Crear `rules/agents-context.md` con el contenido de la regla genérica
- [ ] Modificar `setupClaudeCode()` en `src/commands/init.ts` para copiar la regla
- [ ] Compilar con `npm run build` y verificar creación del archivo

#### Phase 2: Limpiar create-symlinks.sh
Eliminar la sección de symlinks AGENTS.md→CLAUDE.md del script.

- [ ] Eliminar sección de búsqueda de AGENTS.md y creación de symlinks CLAUDE.md
- [ ] Actualizar comentario de cabecera y resumen final del script
- [ ] Compilar y verificar que solo crea symlinks de skills

#### Phase 3: Update path
Modificar el comando update para actualizar la regla en proyectos existentes.

- [ ] En `update.ts`, agregar lógica para copiar `agents-context.md` si existe `.claude/`
- [ ] Incluir el archivo en el manifest de cambios
- [ ] Compilar y verificar con `sdd update` en un proyecto con `.claude/`

### Next Step
Begin with Phase 1: Template + Init.
```

## Key Observations
- 3 phases, each is a vertical slice that can pass tests independently
- Context section explains WHY each file is relevant, not just its path
- Public Contracts include specific function signatures and what changes
- New file template is listed explicitly as a contract
- Each phase ends with a build/verify action item — tests after each phase
- Action items are specific enough to implement without ambiguity
