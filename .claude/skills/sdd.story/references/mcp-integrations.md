# MCP Integrations for Story Creation

Detailed procedures for extracting context from external tools (Jira, Figma) when creating stories.
These steps are conditional — only apply when the user provides a ticket key or Figma URL.

---

## Jira / Project Tracker Integration

**Trigger**: User provides a Jira ticket key (e.g., `PROJ-123`) or URL (e.g., `https://company.atlassian.net/browse/PROJ-123`).

### When MCP tools ARE available
Tools to detect: `getJiraIssue`, `searchJiraIssuesUsingJql`, or equivalent from any project tracker MCP.

1. Parse the ticket key from the user's input (extract `PROJ-123` from a URL if needed).
2. Use the available MCP tool to fetch the issue — retrieve the summary, description, and acceptance criteria if present.
3. Fetch the issue comments and filter for relevant context (skip automated/bot comments, focus on human discussion
   that adds detail to the requirements).
4. Present a concise summary of the extracted context to the user.

### When MCP tools are NOT available
- Inform the user: *"No project tracker MCP detected. Install one (e.g., Atlassian MCP) in your `.mcp.json` or
  Claude Code settings. Run `sdd mcp` to see recommendations."*
- Ask the user to paste the ticket content manually instead.

### After extraction
- Ask the user: *"Do you want to add or modify any additional context?"* Accept free-form input.
- Use the combined context (ticket content + user additions) as the base description for the story.
- Skip the regular user description prompt since the context has already been gathered.

### `original_request.md` must include:
- **Jira ticket link**: the full URL to the ticket
- **Jira ticket key**: e.g., `PROJ-123`
- The original description and relevant comments extracted from the ticket
- Any additional context the user provided

---

## Figma Design Integration

**Trigger**: User provides a Figma URL (e.g., `https://figma.com/design/{fileKey}/{name}?node-id={nodeId}`).

### When Figma MCP tools ARE available
Tools to detect: `get_design_context`, `get_screenshot`, `get_variable_defs`.

1. Parse the Figma URL to extract `fileKey` and `nodeId`. Convert `nodeId` from URL format (`42-15`) to
   API format (`42:15`) by replacing `-` with `:`.
2. Call `get_design_context(fileKey, nodeId)` to fetch layout, components, and design token data.
3. Call `get_screenshot(fileKey, nodeId)` to capture a visual reference of the design.
4. Call `get_variable_defs(fileKey)` to retrieve design system variables (colors, spacing, typography).
5. Present a concise summary of the extracted design context to the user.

### When Figma MCP tools are NOT available
- Inform the user: *"No Figma MCP detected. Install it via:
  - **Claude Code (recommended):** `claude plugin install figma@claude-plugins-official`
  - **Other agents / per-project:** add `{"figma": {"url": "https://mcp.figma.com/mcp"}}` to your `.mcp.json`.
  Run `sdd mcp` to see all recommendations."*
- Ask the user to describe the design manually instead (layout, colors, components, spacing).

### After extraction
- Ask the user: *"Do you want to add or modify any visual context?"* Accept free-form input.
- Use the design context to populate the **Visual Spec** section in the story template.
- This section is **in addition to** the regular story content — the story still needs Description and AC.
- Add visual-specific acceptance criteria (layout matches, colors match, typography matches) to the AC list.

### `original_request.md` must also include:
- **Figma URL**: the full URL provided by the user
- **File key**: extracted from the URL
- **Node ID(s)**: extracted from the URL
- Summary of the design context extracted from Figma MCP (or manual description if MCP was not available)

---

## Combining Jira + Figma

A user may provide both a Jira ticket AND a Figma URL in the same request. Process both:
1. Fetch Jira context first (step 3)
2. Fetch Figma context second (step 3b)
3. Combine both into the story
