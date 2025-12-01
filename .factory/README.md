# Factory Droid Configuration

This directory contains configuration and instructions for Factory Droid (Cursor) agents.

## Directory Structure

```
.factory/
├── droids/             # Droid definitions (specialized subagents)
│   ├── api-developer.md
│   ├── code-reviewer.md
│   ├── codebase-auditor.md
│   ├── e2e-tester.md
│   ├── test-engineer.md
│   └── ui-builder.md
│
├── commands/           # Command definitions (user-facing commands)
│   ├── audit-codebase.md
│   ├── build-api.md
│   ├── build-ui.md
│   ├── e2e-test.md
│   ├── review.md
│   └── write-tests.md
│
├── skills/             # Skill definitions (domain knowledge)
│   ├── django-development/
│   ├── frontend-ui-integration/
│   ├── service-integration/
│   └── ...
│
├── hooks/              # Git hooks and automation scripts
├── mcp.json            # MCP server configuration
└── settings.json       # Factory Droid settings
```

## Important: Resource Isolation

**Factory Droid agents MUST ONLY reference content from `.factory/` directory:**

- Skills: `.factory/skills/`
- Commands: `.factory/commands/`
- Droids: `.factory/droids/`

**DO NOT reference `.opencode/` directory** - it is for a different system (OpenCode).

## File Format

### Droid Files (`.factory/droids/*.md`)
- YAML frontmatter with `name`, `description`, `model`, and `tools`
- Droid instructions and capabilities
- Must include resource isolation notice

### Command Files (`.factory/commands/*.md`)
- Command usage instructions
- References to droids via `subagent_type`

### Skill Files (`.factory/skills/*/SKILL.md`)
- YAML frontmatter with `name` and `description`
- Domain-specific knowledge and patterns
- Optional `references/` and `examples/` subdirectories

## Related Configuration

- `.cursor/mcp.json` - Cursor MCP server configuration
- `AGENTS.md` - Agent guidelines and patterns
