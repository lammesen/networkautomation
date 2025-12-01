#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
Task orchestration: classify (trivial/focused/complex), match to subagent (code-reviewer, test-engineer, ui-builder, api-developer, e2e-tester, codebase-auditor), decide delegate or handle. Use task-orchestration skill.
EOF
exit 0
