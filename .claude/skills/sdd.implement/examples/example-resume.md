# Example: Resume Output (3-phase implementation)

## Input
- Plan: `specs/1773200755_replace_claude_symlinks_with_rules/plan.md`
- Plan had 3 phases: Template + Init, Clean script, Update path
- All phases passed tests

## Output

### File: `specs/1773200755_replace_claude_symlinks_with_rules/resume.md`

```markdown
**Created at**: 2026-03-11
**Based on plan**: @specs/1773200755_replace_claude_symlinks_with_rules/plan.md
**Based on story**: @specs/1773200755_replace_claude_symlinks_with_rules/story.md

# Resume: Reemplazar symlinks AGENTS.md→CLAUDE.md con regla en .claude/rules/

### Executive Summary
Se eliminó la creación de symlinks `CLAUDE.md → AGENTS.md` del flujo de setup de Claude Code y se
reemplazó con un archivo de regla `.claude/rules/agents-context.md` que instruye a Claude Code a leer
automáticamente los `AGENTS.md` de cualquier directorio. Esto elimina problemas de portabilidad
cross-platform, la necesidad de ejecutar un script de mantenimiento cada vez que se agrega un
`AGENTS.md`, y archivos derivados en el repositorio.

### Technical Summary
- Creado template `templates/base/.ai/scripts/claude-code/rules/agents-context.md` con la regla genérica
- Modificado `setupClaudeCode()` en `src/commands/init.ts` para copiar la regla a `.claude/rules/`
- Eliminada toda la sección de symlinks AGENTS.md→CLAUDE.md de `create-symlinks.sh`
- Extendido `src/commands/update.ts` para detectar proyectos Claude Code y actualizar la regla
- El archivo de regla se incluye en el manifest de cambios del update

### Phases Completed
- [x] **Phase 1**: Template + Init — Creado el archivo de regla en templates y modificado
  `setupClaudeCode()` para copiarlo a `.claude/rules/`
- [x] **Phase 2**: Limpiar create-symlinks.sh — Eliminada la sección de AGENTS.md symlinks,
  manteniendo solo la lógica de skills
- [x] **Phase 3**: Update path — Extendido `update.ts` para actualizar la regla en proyectos
  Claude Code existentes
```

## Key Observations
- Executive Summary: 2 sentences, business value, accessible to non-technical reviewers
- Technical Summary: 5 bullets, key decisions and files modified
- Phases Completed: checked checkboxes with one-line summary per phase
- Language matches the user's language (Spanish)
- Links to both plan and story using @path notation
