#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
cd "$CWD"

[[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]] && exit 0

if [[ "$FILE_PATH" =~ \.py$ && "$FILE_PATH" == *backend/webnet* ]]; then
    [[ -x backend/venv/bin/ruff ]] && backend/venv/bin/ruff check --fix "$FILE_PATH" 2>/dev/null || true
    [[ -x backend/venv/bin/black ]] && backend/venv/bin/black --quiet "$FILE_PATH" 2>/dev/null || true
    [[ -x backend/venv/bin/isort ]] && backend/venv/bin/isort --quiet "$FILE_PATH" 2>/dev/null || true
fi

if [[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx)$ ]]; then
    if [[ -f backend/node_modules/.bin/prettier ]]; then
        (cd backend && node_modules/.bin/prettier --write "../$FILE_PATH" 2>/dev/null || true)
    elif command -v prettier &>/dev/null; then
        prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
fi

if [[ "$FILE_PATH" =~ \.(css|scss)$ && -f backend/node_modules/.bin/prettier ]]; then
    (cd backend && node_modules/.bin/prettier --write "../$FILE_PATH" 2>/dev/null || true)
fi

if [[ "$FILE_PATH" =~ \.json$ && command -v jq &>/dev/null ]]; then
    jq empty "$FILE_PATH" 2>/dev/null || echo "⚠️ Invalid JSON: $FILE_PATH" >&2
fi

if [[ "$FILE_PATH" =~ \.html$ && "$FILE_PATH" == *templates* ]]; then
    command -v djlint &>/dev/null && djlint --reformat "$FILE_PATH" 2>/dev/null || true
fi

exit 0
