---
description: Initialize a project with AGENTS.md and docs structure for AI agent navigation. Use when the user says "initialize project", "setup docs", "generate AGENTS.md", or wants to create the knowledge base from scratch.
---

# Spec Driven Development (SDD): Project Initialization
A skill that analyzes a project from scratch and generates the documentation context (AGENTS.md files and docs
knowledge base) so that AI agents can self-navigate efficiently without reading the entire codebase.

# When to Use This Skill
## Ideal scenarios:
- When a project is new and has no AI agent context (no AGENTS.md, no docs folder).
- When the existing documentation is outdated and needs to be regenerated from scratch.


# Core Principles

1. **AGENTS.md files are navigation indices**, not documentation. They tell the agent *where to look*, not *what to know*.
2. **Docs files are the knowledge base**. Each file covers one focused topic with enough detail for an agent to act on it.
3. **Folder and file names must be self-descriptive** so an agent can pick the right file by name alone, without reading all of them.
4. **Write for machines first, humans second**. Concise, structured, scannable. No filler prose.


# How to initialize a project

1. **Read the project settings.** Read `.sdd.json` to resolve the dynamic paths for `docs` and `specs`.
   Use these paths throughout the rest of the steps. Example: if `paths.docs` is `"docs"`, then the docs folder is
   `docs/` relative to the project root. If the file does not exist yet, inform the user to run `sdd init` first.

2. **Identify the project root.** If the user provided a path, use it. If not, use the current working directory.

3. **Identify legacy code to exclude.** Before exploring the codebase, ask the user if there are files or folders
   containing legacy code whose patterns should NOT be documented as conventions. Use AskUserQuestion.

   Example question:
   - "Are there files or folders with legacy code that should NOT be treated as reference for conventions?
     If so, please list them (e.g., `src/old-module/`, `src/services/LegacyService.java`). I will read them to
     understand existing behavior, but I will NOT document their patterns as the project standard."

   If the user provides a list:
   - Read those files/folders to understand what they do, but treat them as **anti-patterns**.
   - When documenting conventions, use only the non-legacy code as reference.
   - If legacy code conflicts with the patterns found in non-legacy code, document the non-legacy pattern as the
     standard and note the legacy code as an exception to avoid replicating.

   If the user says there is no legacy code to exclude, proceed normally.

4. **Ask testing preferences.** Before starting the project discovery, ask the user about their testing requirements
   using AskUserQuestion. This information will guide whether testing documentation is generated and what it contains.

   Ask the following questions in a single round (up to 3 questions):

   1. "Do you want to include testing guidelines in the generated documentation?"
      - Options: Yes / No
   2. "What coverage level or percentage are you targeting, and which layers or folders should testing focus on?"
      - Free text (e.g., "80% coverage on src/services/ and src/domain/", "unit tests for all use cases",
        "integration tests for API controllers only")
   3. "Is there anything else to clarify about testing in this project? (e.g., preferred test runner, mocking strategy,
      specific patterns to follow or avoid)"
      - Free text, optional

   Based on the user's answers:
   - If the user says **yes** to testing: store the preferences (coverage target, layers/folders, clarifications)
     and use them in steps 5.4, 7, and 8.
   - If the user says **no** to testing: skip sub-step 5.4 (Testing) during discovery, do not include the `testing/`
     folder in the docs structure (step 7), and do not generate testing documentation (step 8).

   Note: Questions 2 and 3 should only be asked if the user answers "yes" to question 1.

5. **Deep Project Discovery.** Thoroughly explore the project to understand it before writing anything.
   Follow the complete checklist in **`references/discovery-checklist.md`** — it covers 8 categories:

   - 5.1 Project Identity (tech stack, runtime, monorepo detection)
   - 5.2 Architecture (folder structure, patterns, dependency rules)
   - 5.3 Code Conventions (naming, DTOs, error handling, linting)
   - 5.4 Testing (conditional — skip if user said no in step 4)
   - 5.5 Database (migrations, schema, entity relationships)
   - 5.6 Configuration & Execution (env vars, startup, infrastructure)
   - 5.7 Business Domain (entities, terminology, workflows)
   - 5.8 API Surface (routes, conventions, documentation)

   Do not guess — read actual files. If legacy files were identified in step 3, read them for context
   but do NOT use their patterns as the project standard.

6. **Clarify ambiguities with the user.** After discovery, evaluate whether any of the following situations apply. If
   so, ask the user using AskUserQuestion **before writing any documentation**:

   Ask questions only when the answer materially changes the documentation. Do NOT ask if the information can be
   reasonably inferred from the codebase.

   Situations that require clarification:
   - **Conflicting conventions**: you found multiple patterns for the same thing (e.g., some files use camelCase,
     others snake_case) and it's unclear which is the standard.
   - **Unclear architecture boundaries**: layers or modules overlap and you can't determine the intended dependency
     direction.
   - **Missing or outdated configuration**: config files exist but seem incomplete or contradict the actual code.
   - **Ambiguous testing strategy**: tests exist but follow no clear pattern across layers.
   - **Domain terminology**: business terms are used inconsistently across the codebase.

   Ask **up to 3 targeted questions** in a single round using AskUserQuestion. If the answers are sufficient,
   proceed. If not, you may do **one additional round** of clarification. Never exceed 2 rounds.

   Example questions:
   - "I found both camelCase and snake_case in service names. Which convention should be documented as the standard?"
   - "The domain layer has direct database imports in some files. Is this intentional or a violation of the architecture?"
   - "I see two different error handling patterns (exceptions vs Result types). Which should be the documented approach?"

7. **Design the `{paths.docs}/` structure.** Based on your discovery, design the folder structure. Use ONLY the folders
   that are relevant — do not create empty folders for categories with no content.

   > **Note**: Only include the `testing/` folder if the user indicated in step 4 that they want testing documentation.
   > If the user said no to testing, omit the `testing/` folder entirely from the structure.

   Reference structure (adapt to what you discovered):

   ```
   {paths.docs}/
   ├── architecture/
   │   ├── architecture-principles.md    # Layer rules, dependency direction, enforcement
   │   ├── project-structure.md          # Folder tree with brief descriptions
   │   └── [pattern]-violations.md       # Common mistakes and how to avoid them (only if relevant)
   ├── business/
   │   ├── glossary.md                   # Domain-specific terms and definitions
   │   └── [workflow-name].md            # Per-workflow business flow documentation
   ├── code/
   │   ├── code-style.md                 # Naming, formatting, linting rules
   │   └── [layer-name]/                 # One subfolder per architectural layer
   │       └── conventions.md            # Patterns, examples, do/don't for that layer
   ├── database/
   │   ├── data-model.md                 # ER diagram (Mermaid) + entity descriptions
   │   └── migrations.md                 # Migration conventions and naming rules
   ├── configuration/
   │   ├── environment-variables.md      # All env vars with descriptions, required/optional
   │   └── key-files.md                  # Important files an agent should know about
   ├── how-to-run/
   │   └── execute.md                    # How to start, build, and run the project
   └── testing/                          # Only if user opted in to testing docs (step 4)
       ├── testing-guidelines.md         # Strategy per layer, what to test, what not to test
       ├── test-conventions.md           # Test file naming, structure, assertion style
       └── run-tests.md                  # How to run tests — must prioritize paths.run_tests script
   ```

   File naming rules:
   - Use **lowercase kebab-case** for all file and folder names
   - Names must be **self-descriptive**: an agent should know the topic from the name alone
   - Prefer specific names over generic ones: `usecase-conventions.md` > `patterns.md`
   - One topic per file. If a file grows beyond 200 lines, split it

8. **Write the documentation.** Write each doc file following these guidelines:

   Content rules:
   - Start with a brief 1-2 sentence summary of what this document covers
   - Use headers (`##`, `###`) to structure the content — agents scan headers to find what they need
   - Include **concrete code examples** from the actual project (not generic examples)
   - Use tables for reference data (env vars, field mappings, etc.)
   - Use Mermaid diagrams for architecture, flows, and data models
   - Write Do/Don't sections for conventions that are easy to get wrong
   - Keep files focused: 50-200 lines is ideal, never exceed 400

   Quality checks:
   - Every code example must compile/run (use real code from the project)
   - Every convention must be backed by evidence from the codebase
   - No aspirational documentation — only document what IS, not what SHOULD BE
   - No redundancy across files — each fact lives in exactly one place

   **Exception — Testing guidelines when no tests exist yet**: If the user opted in to testing documentation (step 4)
   but the project has no existing tests, write the testing guidelines as **requirements to implement**. Clearly
   state that no tests exist yet and document the user's desired strategy (coverage targets, layers to cover,
   preferred tools or patterns). This is a valid exception to the "no aspirational documentation" rule because the
   user explicitly requested it.

   **Testing `run-tests.md` structure**: When generating the `testing/run-tests.md` file, always structure it as:
   1. **Primary method**: the script from `.sdd.json` `paths.run_tests` (e.g., `./scripts/run-tests.sh`). Explain
      that this uses Docker for consistent, reproducible results.
   2. **Fallback only**: direct test framework commands (e.g., `npm test`, `pytest`, `go test`) — labeled as
      "for quick local debugging only, not for implementation workflows".
   If `paths.run_tests` is not configured or the script doesn't exist yet, note that the user should run
   `/sdd.util.makeruntest` to generate the Docker-based test scripts.

9. **Create AGENTS.md navigation files.** Use the templates and guidelines in
   **`references/agents-md-templates.md`** to create:

   - **Root AGENTS.md**: project overview, key commands, routing table to `{paths.docs}/` folders.
   - **Subdirectory AGENTS.md files**: one per major code directory (e.g., `src/domain/`, `src/application/`),
     pointing to the relevant docs scope. Only create these where the routing adds value — if the project
     has a flat structure, the root AGENTS.md is sufficient.

10. **Present results to the user.** After creating everything:
   - Show the complete `{paths.docs}/` folder tree you created
   - List all AGENTS.md files and their locations
   - Provide a brief summary of what was documented and any gaps you identified
   - Ask the user if they want to adjust, add, or remove anything


# Important Notes

- **Do NOT skip step 5 (Discovery)**. The quality of the docs depends entirely on the depth of discovery.
- **Do NOT create placeholder files**. Every file must have real, useful content from the project.
- **Do NOT duplicate content** across docs files. Each piece of information lives in one place.
- **Do NOT put detailed documentation inside AGENTS.md files**. They are indices, not encyclopedias.
- **Testing aspirational docs are allowed** only when the user explicitly opted in to testing documentation (step 4) but the project has no existing tests. In this case, document the desired testing strategy as requirements to implement.

# Language

Write all documentation in the **same language the user uses**. If the user writes in Spanish, all docs
and AGENTS.md files must be in Spanish. If in English, use English.
Code examples, file names, and technical terms remain in English regardless of the documentation language.

# Additional Resources

### Reference Files
- **`references/discovery-checklist.md`** — Complete checklist for all 8 discovery categories (5.1-5.8)
- **`references/agents-md-templates.md`** — Templates and guidelines for root and subdirectory AGENTS.md files

### Examples
- **`examples/example-output.md`** — Complete init output for a TypeScript CLI project (AGENTS.md + docs structure)
