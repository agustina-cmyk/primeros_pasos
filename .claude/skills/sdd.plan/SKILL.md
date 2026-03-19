---
description: Create an implementation plan from a user story. Use when the user says "write a plan", "create a plan", "plan this story", or provides a story path to plan.
---

# Spec Driven Development (SDD): Implementation Plan Creation
A skill that creates an implementation plan based on an existing user story, following the provided template and guidelines.

# When to Use This Skill
## Ideal scenarios:
- When the user needs to create an implementation plan based on a user story to develop with spec-driven development.


# How to create a plan

1. **Read and validate the project settings.** Read `.sdd.json` to resolve the dynamic paths for `docs` and `specs`.
   Use these paths throughout the rest of the steps. Example: if `paths.docs` is `"docs"`, then the docs folder is
   `docs/` relative to the project root. Same for `paths.specs`.

   **If `.sdd.json` does not exist or is missing `paths.docs` / `paths.specs`**: stop and inform the user:
   *"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."*
   Do NOT proceed without valid paths.

2. **Read project documentation for context.** Always read these foundational folders:
    - @{paths.docs}/code/
    - @{paths.docs}/architecture/
    - @{paths.docs}/testing/

   Then evaluate the story to identify which additional docs are relevant (database, business logic,
   API, config, etc.). Follow the guide in **`references/contextual-docs.md`** to determine which
   extra documentation to read based on the story's scope. Skip any folders that don't exist.

3. **Identify the source story.** If the user provided the path to the user story, read it. If the user did NOT
   provide the path, ask the user which story this plan is based on using AskUserQuestion. Do NOT proceed until you
   have a valid story to base the plan on.

   Example question:
   - "Which user story should this plan be based on? Please provide the path to the story file (e.g., `{paths.specs}/<folder>/story.md`)."

4. **Read the story and check for existing plans.** Read the story file and understand the requirements, acceptance
   criteria, and any additional context provided. Then:

   - Check the **Status** field in the story. If the status is **not** `Draft`, it means a plan was likely already
     created from this story.
   - Check if a `plan.md` file already exists in the same folder as the story.
   - If a `plan.md` already exists, the new plan file must be named `{unix_timestamp}_plan.md` (e.g.,
     `1740000000_plan.md`) to avoid overwriting the existing plan.
   - If no `plan.md` exists, use the default name `plan.md`.

5. Ask the user if they want to define or adjust the public contracts and implementation phases. Accept any level of
   detail — from a vague idea to a detailed specification.

   We understand as public contracts the following things:
    - Application services to add, modify or remove, and the methods signatures of each one of them.
    - Domain events to add, modify or remove, and the attributes of each one of them.
    - Test suites to add, modify or remove, and all the test cases inside each one of them.
    - Database schemas to add, modify or remove, and the tables inside each one of them.
    - Text copies shown to end users in the UI or emails to add, modify or remove.
    - UI/Design contracts (only when the story contains a **Visual Spec** section):
      - UI components to create, modify or remove, referencing specific Figma nodes.
      - Design token mappings: Figma token → project token (e.g., `primary/#1A73E8` → `--color-primary`).
      - Assets to download from Figma (icons, images) with their Figma node references.

   If the user does not provide the public contracts, suggest them based on the story description.
   Do the same with the implementation phases.

   **When the story has a Visual Spec section:** the implementation phases should include action items
   that reference specific Figma nodes (e.g., "Implement layout matching Figma node 42:15"). This gives
   the implementer concrete visual targets for each task.

6. Clarify (only if needed). Evaluate whether the information is clear enough to write a well-defined plan. If there
   are ambiguities or missing information that would significantly affect the plan quality, ask **up to 3 targeted
   questions** to fill in the gaps.

   Ask questions only when the answer materially changes the plan. Do NOT ask if:
    - The information can be reasonably inferred from the story or the codebase.
    - The missing detail is minor and can be left open for the implementer to decide.

   Ask questions **one round at a time** using AskUserQuestion (max 3 questions per round). If the answers are
   sufficient, proceed. If not, you may do **one additional round** of clarification. Never exceed 2 rounds.

7. Propose the plan to the user for approval. IMPORTANT: Do not start creating the plan file until the user has
   agreed on the specific contracts to be considered and the implementation phases.

8. Load the `template.md` file in the current folder and fill it with the information gathered from the user. Make
   sure to follow the writing guidelines in the template.

9. Save the plan in a new file inside the `{paths.specs}` directory (from settings.json), in the **same folder as the story** it is based on.
   - If no previous `plan.md` exists in that folder, name the file `plan.md`.
   - If a `plan.md` already exists (detected in step 3), name the file `{unix_timestamp}_plan.md` (e.g.,
     `1740000000_plan.md`), where the timestamp is the current date in seconds.

10. **Update the source story.** After saving the plan file, update the story file:
   - If the story **Status** is `Draft`, change it to `In Progress`.
   - If the story **Status** is already `In Progress` (or any other non-Draft status), leave it as is.
   - Do NOT modify the **Plan implemented** field at this point — that field is only updated later when the plan is
     actually implemented (i.e., by the `sdd.implement` skill or equivalent).


# Important Notes

- **Do NOT create the plan file until user approval.** Step 7 requires explicit user agreement on
  contracts and phases before writing the plan.
- **Each phase must be a vertical slice** that can pass tests independently. Avoid phases that are
  only "setup" or "cleanup" with no testable outcome.
- **Plan goes in the same folder as the story.** Never create a new spec folder for a plan.
- **Omit empty contract categories.** If there are no database changes, do not include a "Database: N/A"
  line — simply omit the category.

# Language

Write in the **same language the user used**. If the user wrote in Spanish, write the plan in Spanish.
If they wrote in English, write in English. Template field names (Status, Created at, etc.) stay in English.

# Additional Resources

### Reference Files
- **`references/contextual-docs.md`** — Guide for which project docs to read based on the story's scope

### Examples
- **`examples/example-basic.md`** — Simple 2-phase plan (text-only changes)
- **`examples/example-multiphase.md`** — Complex 3-phase plan with code changes and function signatures
