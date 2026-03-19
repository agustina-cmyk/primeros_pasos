# Contextual Documentation Reading Guide

When creating a plan, evaluate the user story to determine which areas of the project documentation
are relevant. Not all docs exist in every project — read only what is available and pertinent.

## How to Use This Guide

1. Read the story's description and acceptance criteria.
2. Identify which categories below are affected by the story.
3. For each affected category, look for matching documentation under `{paths.docs}/`.
4. If a referenced folder or file does not exist, skip it silently — do not ask the user about it.

## Documentation Categories

| Story involves...                          | Look for docs in                                            |
|--------------------------------------------|-------------------------------------------------------------|
| Database changes (new columns, tables, migrations) | `{paths.docs}/database/` — ERD diagrams, migration guides  |
| Business logic or domain flows             | `{paths.docs}/business/` — flow descriptions, business rules, domain queries |
| API endpoints (new or modified)            | `{paths.docs}/collection/` — API collections, endpoint specs |
| Environment or config changes              | `{paths.docs}/configuration/` — environment variables, config guides |
| UI components or frontend changes          | `{paths.docs}/frontend/` — component library, design system |
| Authentication or authorization            | `{paths.docs}/security/` — auth flows, permission models   |
| Infrastructure or deployment               | `{paths.docs}/infrastructure/` — deployment guides, CI/CD  |

## Always Read (regardless of story type)

These folders provide foundational context for any plan:

- `{paths.docs}/code/` — Code conventions, naming, style guides
- `{paths.docs}/architecture/` — Project structure, dependencies, module boundaries
- `{paths.docs}/testing/` — Testing conventions, strategies, coverage expectations

## Notes

- The folder names above are conventions. The actual names may vary per project — use the patterns
  as guidance, not exact paths.
- When a story spans multiple categories (e.g., new API endpoint with database migration), read docs
  from all relevant categories.
- If the project has minimal documentation, rely more heavily on reading the actual codebase for context.
