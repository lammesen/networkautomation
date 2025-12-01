#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${FACTORY_PROJECT_DIR:-$(pwd)}"
PROGRESS_FILE="$PROJECT_DIR/progress.md"
INPUT=$(cat)
SUBAGENT_NAME=$(echo "$INPUT" | jq -r '.subagent_type // "unknown"')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "- [$TIMESTAMP] Subagent \`$SUBAGENT_NAME\` completed" >> "$PROGRESS_FILE"
exit 0
