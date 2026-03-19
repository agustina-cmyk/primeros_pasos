# AGENTS.md Templates

Templates for root and subdirectory AGENTS.md files. Adapt to the specific project.

---

## Root AGENTS.md Template

```markdown
# AGENTS.md

[2-3 sentence project overview: what it is, tech stack, purpose]

## Key Commands

[Table or list of essential commands: build, run, test, lint, etc.]

## Before Modifying Code

Read the relevant documentation based on what you're about to do:

| What you need to understand             | Read these docs                              |
|-----------------------------------------|----------------------------------------------|
| Architecture rules and layer boundaries | `{paths.docs}/architecture/`                     |
| Code conventions for a specific layer   | `{paths.docs}/code/[layer-name]/`                |
| Testing approach and conventions        | `{paths.docs}/testing/`                          |
| Database schema or migrations           | `{paths.docs}/database/`                         |
| Business domain and workflows           | `{paths.docs}/business/`                         |
| How to run or configure the project     | `{paths.docs}/how-to-run/`, `{paths.docs}/configuration/` |

To identify which files are relevant inside each folder, check the file names — they are self-descriptive.
```

### Root AGENTS.md Guidelines
- Give a 2-3 sentence project overview (what it is, tech stack, purpose)
- List key commands (build, run, test) with the exact shell commands
- Act as a **routing table**: for each type of task, point to the right `{paths.docs}/` folder
- Reference the most critical docs by path
- Only include rows in the routing table for doc folders that actually exist

---

## Subdirectory AGENTS.md Template

```markdown
**IMPORTANT**: Before modifying or creating any file in this directory, read the relevant
documents in `{paths.docs}/code/[layer-name]/`.
To identify which files are relevant, check the file names — they are self-descriptive.
```

### Subdirectory AGENTS.md Guidelines
- States what this directory contains (1 sentence)
- Points to the specific docs folder relevant to this scope
- Only create subdirectory AGENTS.md files where the routing adds value
- If the project has a flat structure with no clear layers, the root AGENTS.md is sufficient
