---
description: Investigate code, debug issues, brainstorm solutions, and discuss technical decisions without modifying any files. Use when the user says "think about", "investigate", "analyze", "why does", "what happens if", "how could we", "review this", "debug this", or asks questions about the codebase.
---

# SDD: Think Mode

A skill that puts the agent in investigation and discussion mode — read code, analyze, propose options,
and debate with the user, but **never modify files**.

# When to Use This Skill

## Ideal scenarios:
- Investigating a bug or unexpected behavior ("why does X happen?")
- Understanding how a part of the codebase works ("how does the auth flow work?")
- Brainstorming approaches before implementing ("how could we redesign the config system?")
- Technical review or audit ("review the error handling in commands/")
- Evaluating tradeoffs between options ("should we use X or Y approach?")
- Exploring impact of a potential change ("what breaks if we remove this interface?")


# How to investigate

1. **Read project context.** Read `.sdd.json` to resolve `paths.docs` and `paths.specs`.
   Skim the relevant `{paths.docs}/` files to understand the project architecture and conventions.

2. **Understand the question.** Identify what the user is asking:
   - **Bug/behavior**: something is broken or unexpected → focus on tracing the issue
   - **Understanding**: how does X work → focus on reading and explaining
   - **Brainstorm**: how could we do X → focus on options and tradeoffs
   - **Review**: is this code good → focus on patterns, gaps, risks
   - **Impact analysis**: what happens if we change X → focus on dependents and side effects

3. **Deep investigation.** Read all relevant source files, tests, and documentation.
   Follow the dependency chain — don't stop at the surface. If the question involves a function,
   read its callers, its callees, and its tests.

   Tools you SHOULD use: Read, Glob, Grep, Agent (for exploration), Bash (for read-only commands
   like `git log`, `git blame`, `git diff`).

4. **Structure your analysis.** Present findings using the format appropriate for the question type:

   **For bugs/behavior:**
   - What's happening (observed behavior)
   - Why it happens (root cause with file:line references)
   - Suggested fix (described, not implemented)

   **For understanding:**
   - How the system works (flow, components involved)
   - Key files and their roles
   - Non-obvious details or gotchas

   **For brainstorm:**
   - Options (2-4 concrete approaches)
   - Tradeoffs for each (complexity, risk, maintenance)
   - Recommendation with reasoning

   **For review:**
   - What's good (patterns worth keeping)
   - Gaps or risks found
   - Suggestions (described, not implemented)

   **For impact analysis:**
   - Direct dependents (files that import/use the thing)
   - Indirect effects (behavior changes, test breakage)
   - Migration effort estimate

5. **Engage in discussion.** After presenting your analysis, stay in conversation mode.
   The user may ask follow-up questions, challenge your analysis, or want to explore
   a different angle. Continue investigating as needed.

6. **Hand off to implementation (optional).** If the user decides to act on the analysis,
   suggest the appropriate next step:
   - "Ready to implement? You can run `/sdd.develop` with this description."
   - "Want me to create a story for this? Run `/sdd.story`."
   - Or simply: "Say the word and I'll start coding."

   Do NOT start implementing unless the user explicitly asks.


# CRITICAL CONSTRAINT

**You MUST NOT modify any files during this skill.** This means:
- Do NOT use the Edit tool
- Do NOT use the Write tool
- Do NOT use Bash to write, append, move, or delete files
- Do NOT create stories, plans, specs, or any artifacts
- Do NOT make commits

The only tools you should use are: **Read**, **Glob**, **Grep**, **Agent** (for exploration only),
and **Bash** (for read-only commands: `git log`, `git blame`, `git diff`, `ls`, etc.).

If you catch yourself about to edit a file — STOP. Present your suggestion verbally instead.


# Language

Respond in the **same language the user used**. Technical terms and code references stay in English.


# Additional Resources

### Examples
- **`examples/example-bug-investigation.md`** — Investigating why config keys aren't merged during sync
- **`examples/example-brainstorm.md`** — Brainstorming a design for a new feature
