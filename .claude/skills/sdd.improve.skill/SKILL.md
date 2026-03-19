---
description: Analyze and improve an existing Claude Code skill based on Anthropic's official skill-creator best practices. Use when the user says "improve skill", "optimize skill", "review skill", or provides a path to a SKILL.md to enhance.
---

# SDD Utility: Improve Skill

A meta-skill that analyzes an existing Claude Code skill against Anthropic's official skill-creator best practices
and applies targeted improvements to make it more effective, better structured, and easier for Claude to execute.

# When to Use This Skill
## Ideal scenarios:
- When the user wants to improve an existing skill following official best practices.
- When a skill produces inconsistent or low-quality results and needs refinement.
- When a skill needs restructuring for progressive disclosure (lean SKILL.md + references/).
- When a skill is missing examples, reference files, or validation scripts.


# How to improve a skill

1. **Identify the target skill.** If the user provided a path to a SKILL.md or skill directory, use it.
   If not, ask using AskUserQuestion:
   - "Which skill do you want to improve? Provide the path to the SKILL.md or its parent directory."

   Resolve the skill directory from the path:
   - If the path points to a file (e.g., `SKILL.md`), use its parent directory.
   - If the path points to a directory, look for `SKILL.md` inside it.
   - If no `SKILL.md` is found, stop and inform the user.

2. **Read the entire skill.** Read ALL files in the skill directory:
   - `SKILL.md` (required)
   - `template.md` (if exists)
   - Everything in `references/`, `examples/`, `scripts/`, `assets/` (if they exist)

   Build a complete picture of the skill's current state.

3. **Read the best practices reference.** Read `references/skill-creator-checklist.md` in THIS skill's
   folder (not the target skill's folder). This contains the official evaluation criteria.

4. **Evaluate the skill against each criterion.** Analyze the target skill using the checklist categories:

   For each category, determine:
   - **Status**: PASS (meets the standard), IMPROVE (partially meets), or MISSING (not addressed)
   - **Finding**: What specifically is good or needs work
   - **Recommendation**: Concrete action to take (only for IMPROVE/MISSING)

   **Categories to evaluate:**

   a. **Frontmatter & Trigger Description**
      - Does the `description` field use natural phrases that match how users actually invoke the skill?
      - Is it specific enough to avoid false triggers but broad enough to catch valid ones?

   b. **Structure & Progressive Disclosure**
      - Is `SKILL.md` lean (ideally under 2000 words for core content)?
      - Is detailed/specialized content moved to `references/` files?
      - Does `SKILL.md` reference its supporting files explicitly?

   c. **Directory Completeness**
      - Does the skill have `references/` for deep knowledge? (when applicable)
      - Does the skill have `examples/` with concrete, real outputs? (when applicable)
      - Does the skill have `scripts/` for validation or automation? (when applicable)

   d. **Content Quality (Written for Claude)**
      - Is the content non-obvious? (avoids things Claude already knows)
      - Does it include procedural knowledge and domain-specific details?
      - Are instructions unambiguous and step-by-step?
      - Are edge cases and failure modes addressed?

   e. **Examples & Reusable Resources**
      - Are there concrete examples of expected input AND output?
      - Are examples realistic (based on real-world usage, not toy examples)?
      - Can Claude use the examples as reference patterns?

   f. **Robustness & Error Handling**
      - Does the skill handle missing inputs gracefully?
      - Does it validate prerequisites before proceeding?
      - Does it have clear stop/ask conditions?

5. **Present the evaluation report to the user.** Show a concise summary:

   ```
   ## Skill Evaluation: {skill name}

   | Category                    | Status  | Finding                          |
   |-----------------------------|---------|----------------------------------|
   | Trigger Description         | PASS    | Clear and natural                |
   | Progressive Disclosure      | IMPROVE | SKILL.md is 3200 words, move...  |
   | Directory Completeness      | MISSING | No examples/ directory           |
   | Content Quality             | PASS    | Well-structured for Claude       |
   | Examples & Resources        | MISSING | No concrete output examples      |
   | Robustness                  | IMPROVE | Missing validation for...        |

   ### Recommended Improvements
   1. [High] Move sections X and Y to `references/detailed-guide.md` (~1200 words)
   2. [High] Add `examples/` with a concrete output example
   3. [Medium] Improve trigger description to include "optimize", "enhance"
   4. [Low] Add `scripts/validate.sh` to check output structure
   ```

   Ask the user: **"Which improvements do you want me to apply? (all / specific numbers / none)"**

6. **Apply the approved improvements.** For each approved improvement:

   **For Progressive Disclosure (moving content to references/):**
   - Identify the sections to extract from SKILL.md
   - Create the reference file with the extracted content
   - Replace the extracted sections in SKILL.md with a brief summary + pointer to the reference file
   - Add an "Additional Resources" section at the end of SKILL.md if not present

   **For Adding Examples:**
   - Generate realistic example files based on the skill's purpose and template (if exists)
   - Create `examples/` directory if needed
   - Add clear file names that describe what each example demonstrates
   - Reference the examples from SKILL.md

   **For Adding Scripts:**
   - Create validation scripts that check the skill's output structure
   - Make scripts executable
   - Reference the scripts from SKILL.md

   **For Improving Trigger Description:**
   - Rewrite the frontmatter `description` using natural user phrases
   - Keep it under 200 characters
   - Include the most common ways users would invoke the skill

   **For Improving Content Quality:**
   - Rewrite ambiguous instructions to be specific
   - Add missing edge case handling
   - Add missing stop/ask conditions
   - Ensure steps are numbered and sequential

   **For Improving Robustness:**
   - Add input validation steps
   - Add prerequisite checks
   - Add clear failure messages

7. **Verify the changes.** After applying improvements:
   - Re-read the modified SKILL.md to ensure it's coherent
   - Verify all file references in SKILL.md point to files that exist
   - Verify the directory structure is clean (no empty directories)
   - Count the word count of SKILL.md — flag if still over 2000 words

8. **Check for template sync.** Look for a corresponding skill in `templates/base/.ai/skills/` with the
   same name. If found, ask the user:
   - "This skill also exists in `templates/base/.ai/skills/{skill-name}/`. Should I apply the same changes there to keep them in sync?"

   If yes, apply the same changes to the template version.

9. **Report results.** Show:
   - Files created or modified (with paths)
   - Before/after word count of SKILL.md
   - New directory structure of the skill
   - Any remaining recommendations that were not applied


# Important Notes

- **Never delete existing content without moving it somewhere.** When applying progressive disclosure,
  always move content to `references/` — never just remove it.
- **Preserve the skill's voice and style.** Improvements should enhance, not rewrite from scratch.
  Keep the original author's intent and approach.
- **Examples must be realistic.** When generating example files, base them on actual usage patterns,
  not generic placeholders.
- **One improvement at a time.** Apply changes incrementally so the user can review each one.
  Do not batch all changes into a single edit.
- **Respect the skill's scope.** Do not add features or capabilities the skill wasn't designed for.
  Only improve how it does what it already does.

# Language

Write all evaluation reports, recommendations, and comments in the **same language the user used**.
Reference files and scripts should be written in **English** (technical convention).
