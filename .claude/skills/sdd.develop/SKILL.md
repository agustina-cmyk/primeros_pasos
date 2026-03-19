---
description: Full SDD pipeline — story → plan → implement in one session. Use when the user says "develop this feature", "build this", "full pipeline", or wants end-to-end development from description to code.
---

# SDD: Full Development Pipeline

Runs story → plan → implement in a single session, auto-detecting where to start.

IMPORTANT: Perform only the actions of the **current step**. Do NOT jump ahead.

## Output Protocol — MANDATORY

**Show ONLY:**
- Progress line per step: `[N/total] Step description...    done`
- Questions requiring user input (contracts, clarifications, approvals)
- Phase results: `PASS` or `BLOCK: [1-line reason]`
- Final artifact paths

**Do NOT output:** full file contents, internal reasoning, verbose explanations.

**Example:**
```
[1/6] Reading project context...                  done
[2/6] Writing story...                            done → specs/.../story.md
[3/6] Defining contracts and phases...
  Proposed contracts: [contract list]
  Phases: [phase list]
  → Do you approve?
[4/6] Writing plan...                             done → specs/.../plan.md
[5/6] Implementing...
  Phase 1/3...  PASS    Phase 2/3...  PASS    Phase 3/3 (final)...  PASS
[6/6] Finalizing...                               done → specs/.../resume.md
```

---

## Phase 0: Initialize and detect state

1. **Read and validate settings.** Read `.sdd.json` — resolve `docs`, `specs`, `run_tests`, and `autoCommit` (defaults to `true` if not present).

   **If `.sdd.json` does not exist or is missing `paths.docs` / `paths.specs`**: stop and inform the user:
   *"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."*

   **If `paths.run_tests` is missing or the script does not exist on disk**: warn the user:
   *"Test runner not configured. Tests will be skipped after each phase. Run `/sdd.util.makeruntest` to generate test scripts."*
   Continue but skip test execution in Phase 3.

2. **Detect starting point.**
   - **Plan path** → check for current phase → go to **Phase 3**
   - **Story path** → note spec folder → go to **Phase 2**
   - **Spec folder** → Glob: has `plan.md` → Phase 3; has `story.md` only → Phase 2; neither → Phase 1
   - **Feature description, Jira key, and/or Figma URL** → go to **Phase 1**
   - **Unclear** → ask: "Start a new feature", "Continue from a story", "Continue from a plan"

   Note: a feature description may include a Figma URL (e.g., `https://figma.com/design/...?node-id=...`).
   This is still a Phase 1 start — the Figma URL will be processed during story creation.

---

## Phase 1: Story

3. **Read project docs.** Read the following for context:
   - `{docs}/code/`
   - `{docs}/architecture/`
   - `{docs}/business/`

4. **Check for external context (optional — Jira and/or Figma).**
   If the user provided a Jira ticket key/URL or a Figma URL, extract context from these sources before
   writing the story. Follow the detailed procedures in **`.claude/skills/sdd.story/references/mcp-integrations.md`**.

   Summary:
   - **Jira ticket**: detect MCP tools → fetch issue + comments → summarize → ask for additions → skip step 5.
   - **Figma URL**: detect MCP tools → fetch design context, screenshot, variables → summarize → populate Visual Spec.
   - Both can be provided in the same request — process both.
   - If MCP tools are unavailable, inform with install instructions and ask for manual input.

5. **If no ticket and no Figma URL:** Ask the user to describe the feature.

6. **Clarify if needed.** Evaluate whether the description is clear enough. If ambiguities exist, ask
   **up to 3 targeted questions** per round (max 2 rounds). Only ask when the answer materially changes the story.

7. **Create spec folder:** `{specs}/{unix_timestamp}_{feature_slug}/`

8. **Write the story.** Read `.claude/skills/sdd.story/template.md`, fill it with gathered information. Save as
   `story.md` in the spec folder. Also save `original_request.md` with the raw user input.

→ Transition to Phase 2.

---

## Phase 2: Plan

9. **Read project docs (if entering directly).** If starting from Phase 2 (story path provided, no Phase 1), read:
   - `{docs}/code/`
   - `{docs}/architecture/`
   - `{docs}/testing/`
   - Evaluate the story and read contextual docs as needed (database, business logic, API collections, config).

10. **Read the story.** If entering from Phase 1, you already have it. Otherwise, read the story file.
    Check for existing `plan.md` in the same folder — if it exists, new plan must be named
    `{unix_timestamp}_plan.md`.

11. **Propose contracts and phases.** Based on the story and project context, propose:
    - Public contracts (services, events, tests, DB schema, UI copies)
    - If the story has a **Visual Spec** section: include **UI/Design** contracts (components with Figma node refs, design token mappings, assets)
    - Implementation phases (with Figma node references in action items when Visual Spec is present)

    Present the proposal to the user.

12. **Clarify if needed.** Max 3 questions, max 2 rounds.

13. **User approval required.** Do NOT proceed until the user agrees on contracts and phases.

14. **Write the plan.** Read `.claude/skills/sdd.plan/template.md`, fill with approved contracts and phases. Save as
    `plan.md` (or `{unix_timestamp}_plan.md` if one already exists) in the spec folder.

15. **Update story status.** If Status is `Draft`, change to `In Progress`.

→ Transition to Phase 3.

---

## Phase 3: Implement

16. **Read the plan and identify current phase.** Read the plan file. Find the current phase: the one indicated in
    "Next Step", or the first phase with unchecked items.

16b. **Offer to create a feature branch (first phase only).** Before executing the first phase, run
    `git branch --show-current` and compare with `baseBranch` from `.sdd.json` (default: `develop`).

    - **If on baseBranch**: ask the user: *"You are on `{baseBranch}`. Create a feature branch?"*
      - If **yes**: suggest a name from the spec folder slug:
        - With Jira ticket: `{TICKET-ID}/{slug}` (e.g., `PROJ-123/add-jwt-validation`)
        - Without ticket: `feat/{slug}` (e.g., `feat/add-jwt-validation`)
        - Strip timestamp prefix from folder name for the slug.
        - Let the user confirm or type a different name.
        - Run: `./scripts/sdd-branch.sh "<branch-name>"`
      - If **no**: continue on current branch.
    - **If already on a feature branch**: skip silently.

    Only runs before the first phase. Do NOT repeat for subsequent phases.

17. **Execute the current phase.** Implement all action items listed in the current phase's to-do list.

17b. **Visual reference (optional).** If the phase references Figma nodes and Figma MCP tools are available,
    use them for visual verification. Follow **`.claude/skills/sdd.implement/references/figma-verification.md`**.
    Skip if Figma MCP is not available.

18. **Run tests.** After completing the phase, run `{run_tests}`.
    - If tests **pass**: proceed to step 18a.
    - If tests **fail**: analyze the failure, fix the issue, re-run tests. Repeat until all tests pass.

18a. **E2E browser verification (optional — Playwright CLI).** Only run this step if **all three**
    conditions are met:
    1. `.sdd.json` contains a `playwright` config section
    2. `playwright-cli` is available (installed via `@playwright/cli`)
    3. The current phase has action items that affect **UI, routes, or visible components**
       (e.g., pages, layouts, forms, navigation). Skip silently for phases that only touch
       backend logic, tests, refactoring, config, or documentation.

    **Open the browser with:** `playwright-cli open --headed {playwright.baseUrl}`
    The `--headed` flag is **mandatory** — without it the user cannot see the browser.
    NEVER run `playwright-cli open` without `--headed`.

    Then follow the detailed procedure in **`.claude/skills/sdd.implement/references/playwright-verification.md`**
    to authenticate (if configured), execute the user flow from the **source story**, and verify the results.

    - If the browser verification reveals issues that tests missed, fix the code **and** update
      the tests, then re-run step 18 before continuing.
    - If any condition above is not met: skip silently.

18b. **Auto-commit (if enabled).** If `autoCommit` is `true` in `.sdd.json` (default), commit the phase's changes
    by running `./scripts/sdd-commit.sh "<type>(<scope>): <description>"`.

    **How to determine the commit message:**
    - **type**: Infer from what the phase did. Use `feat` for new functionality, `fix` for bug fixes,
      `test` for adding/updating tests, `refactor` for restructuring, `docs` for documentation,
      `chore` for config/tooling changes. When a phase mixes types, use the primary one.
    - **scope**: The main module or area affected (e.g., `cli`, `config`, `auth`, `api`).
    - **description**: A concise summary of what the phase accomplished.

    Example: `./scripts/sdd-commit.sh "feat(auth): add JWT token validation"`

    **If the script exits with 0 and reports "No changes to commit"**, that's fine — continue.
    **If the script exits with 1**, read the error and fix the commit message format, then retry.
    **If `autoCommit` is `false`**, skip this step entirely.

19. **Update the plan.** Check the completed action items (`- [x]`). Update the **Next Step** section.

20. **More phases?** Show progress line, return to step 17 for the next phase.

21. **Finalize (all phases done).**
    a. **Write resume.** Read `.claude/skills/sdd.implement/template.md`, fill it. Save as `resume.md` in the spec folder.
    b. **Update plan:** Status → `Done`, Next Step → "All phases completed. See resume.md."
    c. **Update story:** Status → `Done`, Plan implemented → path to plan.
    d. **Offer to create a Pull Request.** Ask the user: *"Do you want to create a Pull Request?"*
       - If **yes**: ask *"Target branch? (default: `{baseBranch}` from .sdd.json)"* — let the user confirm or change.
         Then run: `./scripts/sdd-pr.sh {specs}/<folder>/resume.md <target-branch>`
       - If **no**: inform the user they can create it later with:
         `./scripts/sdd-pr.sh {specs}/<folder>/resume.md`
       - If `gh` is not installed: inform the user and suggest running `./scripts/setup-github-cli.sh` first.

---

# Important Notes

- **One step at a time.** NEVER jump ahead to a future phase or step. Complete current → validate → move on.
- **User approval is mandatory in Phase 2.** Do NOT write the plan until the user agrees on contracts and phases.
- **Output Protocol is mandatory.** Follow the progress line format strictly. No verbose output.
- **Sub-skill resources are authoritative.** When this skill references files from `sdd.story`, `sdd.plan`,
  or `sdd.implement`, those files are the source of truth for the detailed procedures.

# Language

Write all artifacts in the **same language the user used**. Template field names (Status, Created at, etc.)
stay in English.
