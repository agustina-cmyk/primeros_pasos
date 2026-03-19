# Example: Story from Jira Ticket

## Input
User says: "/sdd.story PROJ-456"

MCP returns:
- **Summary**: "Add MCP integration system with Jira support"
- **Description**: "SDD needs an MCP management system so users can list, install, and remove external
  integrations. First MCP: Atlassian (Jira + Confluence)."
- **Comments**: One human comment adding that OAuth 2.1 is required and the `.mcp.json` file must not
  be overwritten.

After summary, user adds: "Quiero que también soporte un comando `sdd mcp status` para ver qué está instalado."

## Output

### File: `specs/1772595735_add_mcp_integration_system/story.md`

```markdown
**Created at**: 2026-03-04
**Status**: Draft
**Original input**: @specs/1772595735_add_mcp_integration_system/original_request.md
**Plan implemented**: —

# Story: Add MCP integration system with Jira support for sdd.story

### Description
SDD necesita un sistema de gestión de MCPs (Model Context Protocol) que permita a los usuarios listar,
instalar y desinstalar integraciones externas de forma sencilla, manteniendo la filosofía opt-in del
paquete. Como primer MCP soportado, se integrará Atlassian (Jira + Confluence) para que el skill
`sdd.story` pueda leer automáticamente tickets de Jira como contexto al crear user stories, eliminando
el paso manual de copiar y pegar información del ticket.

### Acceptance Criteria
- [ ] **Given** un proyecto con SDD inicializado, **When** el usuario ejecuta `sdd mcp list`, **Then**
  se muestra una lista de MCPs disponibles con su nombre, descripción y estado (installed / not installed).
- [ ] **Given** un proyecto con SDD inicializado, **When** el usuario ejecuta `sdd mcp add atlassian`,
  **Then** se agrega la configuración del MCP Atlassian a `.mcp.json` sin sobreescribir entries existentes.
- [ ] **Given** el MCP atlassian instalado, **When** el usuario ejecuta `sdd mcp remove atlassian`,
  **Then** se elimina el entry de `.mcp.json` y se marca como deshabilitado en settings.
- [ ] **Given** un proyecto con SDD inicializado, **When** el usuario ejecuta `sdd mcp status`, **Then**
  se muestra un resumen de MCPs instalados vs disponibles.
- [ ] **Given** el usuario invoca `/sdd.story` con un Jira ticket key pero el MCP NO está instalado,
  **When** el agente procesa el skill, **Then** informa que la integración no está configurada y pide
  pegar el contenido manualmente.

### Additional Context
- **Primer MCP soportado**: Official Atlassian Rovo MCP Server (OAuth 2.1, cloud-hosted).
- **`.mcp.json`**: archivo estándar de Claude Code para MCP servers. SDD debe hacer merge, no overwrite.
- **Zero external dependencies**: solo Node.js built-ins.
```

### File: `specs/1772595735_add_mcp_integration_system/original_request.md`

```markdown
- **Jira ticket link**: https://company.atlassian.net/browse/PROJ-456
- **Jira ticket key**: PROJ-456
- **Summary**: Add MCP integration system with Jira support
- **Description**: SDD needs an MCP management system so users can list, install, and remove external
  integrations. First MCP: Atlassian (Jira + Confluence).
- **Relevant comments**: OAuth 2.1 is required. `.mcp.json` must not be overwritten.

**Additional user context**: Quiero que también soporte un comando `sdd mcp status` para ver qué está instalado.
```

## Key Observations
- Jira ticket content is fetched via MCP and summarized before story creation
- `original_request.md` includes the Jira ticket link, key, description, and comments
- User additions are merged into the story context
- The story language matches the user's language (Spanish in this case)
