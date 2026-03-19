# Figma Visual Verification During Implementation

This procedure applies **only** when a phase's action items reference Figma nodes
(e.g., "Implement layout matching Figma node 42:15") AND Figma MCP tools are available.

If Figma MCP tools are not available, skip entirely — the implementer works from the plan's text
descriptions and Figma node references alone.

---

## Tools to Detect

Check if these Figma MCP tools are available in the current context:
- `get_design_context`
- `get_screenshot`

## Procedure

### Before Implementing UI Tasks
Call `get_screenshot(fileKey, nodeId)` for the referenced Figma nodes to have a visual reference
of the target design.

### Downloading Assets
If action items mention assets to download, use the localhost URLs returned by the Figma MCP server
directly. Do NOT:
- Import new icon packages as a substitute
- Use placeholder images or icons
- Generate SVG approximations

Always use the actual asset from Figma when a localhost source is provided.

### After Implementing UI Tasks
Compare the implementation against the Figma screenshot to verify visual accuracy:
- **Layout**: element positioning, grid alignment, flex/grid structure
- **Colors**: exact color values match design tokens
- **Typography**: font family, size, weight, line height
- **Spacing**: margins, padding, gaps between elements

Note any discrepancies for the user.

**Note:** Visual comparison requires an AI agent with multimodal capabilities (e.g., Claude Code).
