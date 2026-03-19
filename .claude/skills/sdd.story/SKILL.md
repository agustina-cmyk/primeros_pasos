---
description: Create a user story from a description, Jira ticket, or Figma URL. Use when the user says "write a story", "create a ticket", "new story", or provides a Jira key or Figma design to turn into a story.
---

# Spec Driven Development (SDD): User Story Creation
A skill that creates a user story based on the user's description, following the provided template and guidelines.

# When to Use This Skill
## Ideal scenarios:
- When the user needs to create a user story based on the user's description to develop with spec-driven development.


# How to create a story

1. **Read and validate the project settings.** Read `.sdd.json` to resolve the dynamic paths for `docs` and `specs`.
   Use these paths throughout the rest of the steps. Example: if `paths.docs` is `"docs"`, then the docs folder is
   `docs/` relative to the project root. Same for `paths.specs`.

   **If `.sdd.json` does not exist or is missing `paths.docs` / `paths.specs`**: stop and inform the user:
   *"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."*
   Do NOT proceed without valid paths.

2. Before you begin, be sure to read these files in these folders for a better understanding of the project.:
    - @{paths.docs}/code/
    - @{paths.docs}/architecture/
    - @{paths.docs}/business/

3. **Check for external context (optional — Jira and/or Figma).**
   If the user provided a Jira ticket key/URL or a Figma URL, extract context from these sources before
   writing the story. Follow the detailed procedure in **`references/mcp-integrations.md`**.

   Summary:
   - **Jira ticket**: detect MCP tools → fetch issue + comments → summarize → ask for additions → skip step 4.
   - **Figma URL**: detect MCP tools → fetch design context, screenshot, variables → summarize → populate Visual Spec section.
   - Both can be provided in the same request — process both.
   - If MCP tools are unavailable, inform the user with install instructions and ask for manual input.

   **If no ticket and no Figma URL were provided**, proceed to step 4.

4. Ask the user to describe what they want to do or achieve. Accept any level of detail — from a vague idea to a
   detailed
   requirement.

5. Clarify (only if needed) Evaluate whether the description is clear enough to write a well-defined ticket. If there
   are ambiguities or missing
   information that would significantly affect the story quality, ask **up to 3 targeted questions** to fill in the
   gaps.

   Ask questions only when the answer materially changes the ticket. Do NOT ask if:
    - The information can be reasonably inferred from the description.
    - The missing detail is minor and can be left open for the implementer to decide.

   Examples of questions worth asking:
    - "Who is the end user of this feature — internal ops team, external clients, or both?"
    - "Should this replace the current behavior or coexist as an alternative?"
    - "Are there acceptance criteria or edge cases you already have in mind?"

   Ask questions **one round at a time** using AskUserQuestion (max 3 questions per round). If the answers are
   sufficient,
   proceed. If not, you may do **one additional round** of clarification. Never exceed 2 rounds.

6. Load the `template.md` file in the current folder and fill it with the information gathered from the user. Make sure
   to follow the writing guidelines in the template.

7. Save the story in a new file inside the `{paths.specs}` directory (from settings.json) creating a new folder with the
   current unix timestamp.
   Example: `{paths.specs}/1673900800_create_embeddable_changelog_widget/` (unix timestamp is the current date in
   seconds). Inside the folder, create a `story.md` and `original_request.md`.

   If the story was created from a Jira ticket or Figma URL (step 3), the `original_request.md` must include
   the source metadata as specified in **`references/mcp-integrations.md`** (ticket link/key, Figma URL/nodeIds,
   extracted content, and any user additions).


# Important Notes

- **Do NOT create a story without user input.** Even when extracting context from Jira or Figma, always
  confirm with the user before writing the final story.
- **Folder naming convention**: `{unix_timestamp}_{feature_slug}/` — the slug must be lowercase, snake_case,
  and descriptive of the feature (e.g., `1673900800_create_embeddable_changelog_widget`).
- **One story per folder.** Each story gets its own folder under `{paths.specs}`.
- **Do NOT modify existing stories** when creating a new one. Each invocation creates a fresh spec folder.

# Language

Write in the **same language the user used**. If the user wrote in Spanish, write the story in Spanish.
If they wrote in English, write in English. Template field names (Status, Created at, etc.) stay in English.

# Additional Resources

### Reference Files
- **`references/mcp-integrations.md`** — Detailed procedures for extracting context from Jira and Figma via MCP

### Examples
- **`examples/example-basic.md`** — Story created from a plain user description
- **`examples/example-with-jira.md`** — Story created from a Jira ticket with MCP integration

