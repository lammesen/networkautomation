# OpenCode Configuration

This directory contains the OpenCode configuration for the webnet project, migrated from the Factory Droid setup.

## Directory Structure

```
.opencode/
├── agent/           # Specialized agents (formerly "droids")
│   ├── api-developer.md
│   ├── code-reviewer.md
│   ├── codebase-auditor.md
│   ├── e2e-tester.md
│   ├── test-engineer.md
│   └── ui-builder.md
├── command/         # Slash commands
│   ├── audit-codebase.md
│   ├── build-api.md
│   ├── build-ui.md
│   ├── e2e-test.md
│   ├── review.md
│   └── write-tests.md
└── skills/          # Domain-specific skills (OpenCode Skills format)
    ├── ai-data-analyst/
    │   └── SKILL.md
    ├── browser/
    │   └── SKILL.md
    ├── code-review-excellence/
    │   └── SKILL.md
    ├── data-querying/
    │   └── SKILL.md
    ├── django-development/
    │   └── SKILL.md
    ├── frontend-ui-integration/
    │   └── SKILL.md
    ├── internal-tools/
    │   └── SKILL.md
    ├── product-management/
    │   └── SKILL.md
    ├── service-integration/
    │   └── SKILL.md
    ├── task-orchestration/
    │   └── SKILL.md
    └── vibe-coding/
        └── SKILL.md
└── README.md        # This file
```

## Important: Resource Isolation

**OpenCode agents MUST ONLY reference content from `.opencode/` directory:**

- Skills: `.opencode/skills/`
- Commands: `.opencode/command/`
- Agents: `.opencode/agent/`

**DO NOT reference `.factory/` directory** - it is for a different system (Factory Droid/Cursor).

## Hook Alternatives

OpenCode does not have a hook system like Factory Droid. The following table documents what the original hooks did and how to achieve similar functionality:

| Original Hook | Purpose | OpenCode Alternative |
|---------------|---------|---------------------|
| `session-start.sh` | Display orchestration reminder | Use `.opencode/skills/task-orchestration/SKILL.md` skill at session start |
| `format-code.sh` | Auto-format on file edit | Use pre-commit hooks or run `make backend-lint` manually |
| `format-python.sh` | Python-specific formatting | Run `backend/venv/bin/ruff check --fix` and `backend/venv/bin/black` |
| `run-tests.sh` | Auto-run tests on file edit | Run `make backend-test` manually after changes |
| `validate-code.sh` | Block edits to sensitive files | Pre-commit hooks + code review process |
| `git-workflow.sh` | Commit message validation | Use `.pre-commit-config.yaml` with commit-msg hooks |
| `log-subagent.sh` | Log subagent runs to progress.md | Manual logging to progress.md |
| `sync-docs.sh` | Sync documentation | Manual doc updates or CI workflow |

### Recommended Pre-Commit Setup

Add these hooks to `.pre-commit-config.yaml` to replicate hook functionality:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: check-json
      - id: no-commit-to-branch
        args: [--branch, main, --branch, master]
      - id: detect-private-key
      - id: detect-aws-credentials

  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.0.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

### Manual Workflow

When working without hooks, follow this workflow:

1. **Before starting**: Read `.opencode/skills/task-orchestration/SKILL.md` skill to evaluate delegation
2. **After editing Python**: Run `make backend-lint` to format and check
3. **After editing TS/React**: Run `cd backend && npm run format` (if configured)
4. **Before committing**: Run `make backend-test` to verify tests pass
5. **When committing**: Use conventional commit format (e.g., `feat(devices): add bulk import`)
6. **Log progress**: Manually add entries to `progress.md`

## Usage

### Slash Commands

Use these commands in OpenCode:

- `/audit-codebase [scope]` - Run comprehensive security/performance audit
- `/build-api <feature>` - Create DRF viewsets and Celery tasks
- `/build-ui <feature>` - Build HTMX templates and React Islands
- `/e2e-test <workflow>` - Run Playwright browser tests
- `/review <branch>` - Review code for quality and security
- `/write-tests <file>` - Generate pytest test cases

### Agent Delegation

For complex tasks, delegate to specialized agents using the Task tool:

```
Task tool with subagent_type: "code-reviewer"
Task tool with subagent_type: "test-engineer"
Task tool with subagent_type: "ui-builder"
Task tool with subagent_type: "api-developer"
Task tool with subagent_type: "e2e-tester"
Task tool with subagent_type: "codebase-auditor"
```

### Skills

Skills provide domain-specific guidance. Reference them when:

- Starting a session → `.opencode/skills/task-orchestration/SKILL.md`
- Working with Django models → `.opencode/skills/django-development/SKILL.md`
- Building UI components → `.opencode/skills/frontend-ui-integration/SKILL.md`
- Creating APIs → `.opencode/skills/service-integration/SKILL.md`
- Running browser tests → `.opencode/skills/browser/SKILL.md`
- Reviewing code → `.opencode/skills/code-review-excellence/SKILL.md`
- Querying data → `.opencode/skills/data-querying/SKILL.md`
- Building internal tools → `.opencode/skills/internal-tools/SKILL.md`
- Analyzing data → `.opencode/skills/ai-data-analyst/SKILL.md`
- Writing PRDs → `.opencode/skills/product-management/SKILL.md`
- Rapid prototyping → `.opencode/skills/vibe-coding/SKILL.md`

## File Format

### Agent Files (`.opencode/agent/*.md`)
- YAML frontmatter with `name` and `description`
- Agent instructions and capabilities
- Must include resource isolation notice

### Command Files (`.opencode/command/*.md`)
- YAML frontmatter with `description` and `agent` (which agent to invoke)
- Command usage instructions

### Skill Files (`.opencode/skills/{skill-name}/SKILL.md`)
- YAML frontmatter with `name` (matching directory), `description` (min 20 chars), and optional `license`
- Markdown content with domain-specific knowledge
- Patterns and best practices
- Each skill in its own directory following OpenCode Skills plugin format

## Related Configuration

- `opencode.json` - OpenCode main configuration file (MCP servers, models, plugins)
  - Located in project root (project-specific configuration)
  - OpenCode also checks `~/.opencode.json` and `~/.config/opencode/opencode.json` for global config
  - Must include `"opencode-skills"` in the `plugin` array to enable skills discovery

## Migration Notes

This configuration was migrated from `.factory/` (Factory Droid format) to `.opencode/` (OpenCode format) on November 2025.

Key changes:
- Commands moved from `.factory/commands/` to `.opencode/command/`
- Agents (droids) moved from `.factory/droids/` to `.opencode/agent/`
- Skills moved from `.factory/skills/` to `.opencode/skills/` (OpenCode Skills format)
- Hook system replaced with manual workflows and pre-commit hooks
- Frontmatter simplified (OpenCode uses `agent:` in commands, `name:`/`description:` in agents)
- References to "Droid" changed to "agent" or "OpenCode"

The original `.factory/` directory is preserved because both Opencode and Droid Agents are used for this project.
