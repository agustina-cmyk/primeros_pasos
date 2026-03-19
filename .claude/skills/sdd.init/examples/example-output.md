# Example: Init Output for a TypeScript CLI Project

## Input
- Project: `@getvaas/sdd` — a TypeScript CLI tool for Spec Driven Development
- Tech stack: TypeScript, Node.js >=16, zero external runtime dependencies
- User opted out of testing documentation
- No legacy code to exclude

## Output: Root AGENTS.md

```markdown
# AGENTS.md

`@getvaas/sdd` is a TypeScript CLI tool that scaffolds Spec Driven Development (SDD) skills and AI agent
context into any project. It runs on Node.js (>=16) with zero external runtime dependencies.

## Key Commands

| Command | Description |
|---------|-------------|
| `npm run build` | Compile TypeScript (`src/` → `dist/`) |
| `node bin/sdd.js` | Run the CLI locally (default: `init` command) |
| `node bin/sdd.js sync` | Run the `sync` command locally |
| `npm publish` | Publish to GitHub Packages (builds automatically) |

## Before Modifying Code

Read the relevant documentation based on what you're about to do:

| What you need to understand | Read these docs |
|-----------------------------|-----------------|
| Folder tree and component relationships | `docs/architecture/project-structure.md` |
| CLI command pattern and how to add commands | `docs/code/cli-commands.md` |
| Template system and sync model | `docs/code/template-system.md` |
| Naming, imports, and TypeScript conventions | `docs/code/code-style.md` |
| SDD workflow, phases, and artifacts | `docs/business/sdd-concepts.md` |
| How to build, test locally, and publish | `docs/how-to-run/build-and-publish.md` |

To identify which files are relevant inside each folder, check the file names — they are self-descriptive.
```

## Output: Docs Structure

```
docs/
├── architecture/
│   └── project-structure.md          # Folder tree with brief descriptions
├── business/
│   └── sdd-concepts.md               # SDD workflow, phases, artifacts
├── code/
│   ├── cli-commands.md                # CLI command pattern and how to add commands
│   ├── code-style.md                  # Naming, formatting conventions
│   └── template-system.md            # Template system and sync model
└── how-to-run/
    └── build-and-publish.md          # How to build, test, and publish
```

## Output: Subdirectory AGENTS.md (src/commands/)

```markdown
**IMPORTANT**: Before modifying or creating any file in this directory, read `docs/code/cli-commands.md`.
This directory contains the CLI command implementations (init, sync, migrate, mcp).
```

## Key Observations
- No `testing/` folder — user opted out of testing docs
- No `database/` or `configuration/` folders — not relevant for this project
- Root AGENTS.md routing table only includes rows for folders that exist
- Subdirectory AGENTS.md only created for `src/commands/` and `src/utils/` where it adds routing value
- All file names are self-descriptive: `cli-commands.md` not `patterns.md`
- Docs files are focused: one topic each, under 200 lines
