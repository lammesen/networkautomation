#!/usr/bin/env bash
set -euo pipefail

FILE_PATH=$(jq -r '.tool_input.file_path // empty')

if [[ -n "$FILE_PATH" && "$FILE_PATH" == *.py && "$FILE_PATH" == *backend/webnet* && -f "$FILE_PATH" ]]; then
    command -v backend/venv/bin/ruff &>/dev/null && backend/venv/bin/ruff check --fix "$FILE_PATH" 2>/dev/null || true
    command -v backend/venv/bin/black &>/dev/null && backend/venv/bin/black --quiet "$FILE_PATH" 2>/dev/null || true
fi

exit 0
