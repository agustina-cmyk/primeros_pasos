# Example: Basic Story (from user description)

## Input
User says: "Necesito que el comando `sdd init` también pregunte al usuario sus preferencias de testing
antes de generar la documentación, así el skill de init puede crear docs de testing con las convenciones
que el equipo realmente usa."

## Output

### File: `specs/1772173169_add_testing_preferences_to_sdd_init/story.md`

```markdown
**Created at**: 2026-02-27
**Status**: Draft
**Original input**: @specs/1772173169_add_testing_preferences_to_sdd_init/original_request.md
**Plan implemented**: —

# Story: Add testing preference questions to sdd init skill

### Description
The `sdd init` skill currently generates project documentation without understanding the team's testing
conventions, which means the testing docs section either gets skipped or contains generic placeholders.
By asking targeted testing preference questions during initialization (framework, patterns, coverage
expectations), the skill can generate accurate testing documentation from day one, reducing the manual
effort needed to set up the testing section of the project knowledge base.

### Acceptance Criteria
- [ ] **Given** a project being initialized with `sdd init`, **When** the skill reaches the documentation
  generation phase, **Then** it asks the user about their testing preferences (framework, patterns,
  coverage expectations) before generating docs.
- [ ] **Given** the user provides testing preferences, **When** the docs are generated, **Then** a
  `docs/testing/` folder is created with documentation reflecting the stated conventions.
- [ ] **Given** the user declines to answer testing questions, **When** the docs are generated, **Then**
  the testing section is skipped entirely (no placeholder or generic content).
- [ ] **Given** a project with no existing tests, **When** the user opts in to testing preferences,
  **Then** the generated testing docs are marked as requirements/aspirational (not documenting existing
  code).

### Additional Context
The testing preferences should be asked as a single round of up to 3 questions, not a lengthy
questionnaire. The goal is to capture enough signal to generate useful docs, not to exhaustively
configure a test suite.
```

### File: `specs/1772173169_add_testing_preferences_to_sdd_init/original_request.md`

```markdown
Necesito que el comando `sdd init` también pregunte al usuario sus preferencias de testing antes de
generar la documentación, así el skill de init puede crear docs de testing con las convenciones que el
equipo realmente usa.
```

## Key Observations
- Title uses action verb + specific outcome, under 80 chars, no ticket IDs
- Description explains what AND why (2 sentences), product perspective
- AC uses Given/When/Then with checkbox format — covers happy path + edge cases
- Language matches the output language preference (English in this case because the project docs are English)
- No Visual Spec section (no Figma URL was provided)
- Additional Context adds genuine value without repeating the description
