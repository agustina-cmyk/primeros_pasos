# Template
```markdown
**Created at**: [DATE]
**Status**: Draft
**Original input**: @link_path_to_original_input
**Plan implemented**: —

# Story: [FEATURE NAME]

### Description
[What is being requested, why it matters, and what problem it solves — 2-4 sentences, product perspective.]

### Acceptance Criteria
- [ ] **Given** [initial state], **When** [action], **Then** [expected outcome]
- [ ] **Given** [initial state], **When** [action], **Then** [expected outcome]

### Visual Spec (from Figma)
[Only include this section if a Figma URL was provided. Omit entirely otherwise.]
- **Figma file**: [full Figma URL]
- **Nodes**: [nodeId — description] (e.g., 42:15 — Dashboard layout, 42:20 — Sidebar nav)
- **Design tokens**: [key tokens extracted — colors, spacing, typography]
- **Layout**: [grid, spacing, alignment constraints from the design]
- **Acceptance criteria (visual)**:
  - [ ] Layout matches Figma node [nodeId]
  - [ ] Colors match design tokens exactly
  - [ ] Typography matches (font, size, weight, line height)
  - [ ] Spacing and alignment match design constraints

### Additional Context
[Technical notes, references, constraints. Omit if nothing to add.]
```

# Rules
- **Title**: Action verb + specific outcome, under 80 chars. No ticket IDs.
- **Description**: What and why, not how. Product perspective. 2-4 sentences.
- **AC**: Observable, testable. Checkbox format. Happy path + edge cases. 3-6 criteria. No implementation details.
- **Visual Spec**: Only when a Figma URL was provided. Include concrete data from Figma MCP (tokens, nodes, layout). If MCP was not available, include the user's manual description of the design. Omit entire section if no Figma reference.
- **Additional Context**: Only if it adds genuine value. No repeating the description.
- **Language**: Write in the **same language the user used**.
