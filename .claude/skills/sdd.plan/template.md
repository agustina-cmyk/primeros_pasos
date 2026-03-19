# Template
```markdown
**Created at**: [DATE]
**Status**: Draft
**Based on story**: @link_path_to_story

# Plan: [FEATURE NAME]

### Goal
[1-3 sentences — what will be achieved when fully implemented.]

### Context
- `path/to/file.ext` — [why relevant]
- `path/to/folder/` — [why relevant]

### Public Contracts
- **Services**: [method signatures]
- **Domain Events**: [event attributes]
- **Tests**: [test suites and cases]
- **Database**: [schemas/tables]
- **UI/Emails**: [text copies]
- **UI/Design**: [Only when story has Visual Spec] [components with Figma node refs, design token mappings, assets to download]

### Phases

#### Phase 1: [PHASE NAME]
[What this phase accomplishes as a vertical slice.]
- [ ] [Action item 1]
- [ ] [Action item 2]

#### Phase 2: [PHASE NAME]
[What this phase accomplishes as a vertical slice.]
- [ ] [Action item 1]
- [ ] [Action item 2]

### Next Step
[Single sentence — first phase to complete.]
```

# Rules
- **Goal**: 1-3 sentences. What, not how. Align with story AC.
- **Context**: Only directly relevant files. Link to actual paths.
- **Contracts**: Only agreed-upon contracts. Specific signatures. Omit empty categories. Include **UI/Design** only when the story has a Visual Spec section — list components with Figma node references, token mappings, and assets.
- **Phases**: Each phase = vertical slice. Checkboxes for actions. Each phase must pass tests independently. 2-5 phases.
- **Language**: Write in the **same language the user used**.
