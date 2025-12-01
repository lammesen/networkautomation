#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
cd "$CWD"

if [[ -z "$FILE_PATH" || ! "$TOOL_NAME" =~ ^(Write|Edit)$ ]]; then exit 0; fi

if [[ "$FILE_PATH" =~ backend/webnet/api/.*\.py$ ]]; then
    API_NAME=$(basename "$FILE_PATH" .py)
    DOC_PATH="docs/api/${API_NAME}.md"
    [[ ! -f "$DOC_PATH" ]] && echo "⚠️ API file changed; missing $DOC_PATH" >&2
fi

if [[ "$FILE_PATH" =~ \.py$ && -d docs ]]; then
    FILENAME=$(basename "$FILE_PATH")
    REFS=$(grep -rl "$FILENAME" docs/ 2>/dev/null || true)
    [[ -n "$REFS" ]] && echo -e "ℹ️ $FILE_PATH referenced in docs:\n$(echo \"$REFS\" | head -3 | sed 's/^/  - /')" >&2
fi

if [[ "$FILE_PATH" =~ \.py$ && -f "$FILE_PATH" ]]; then
    PUBLIC_COUNT=$(grep -E "^def [^_]|^    def [^_]" "$FILE_PATH" 2>/dev/null | wc -l | tr -d ' ')
    [[ "$PUBLIC_COUNT" -gt 3 ]] && echo "⚠️ Consider docstrings for public funcs in $FILE_PATH" >&2
fi

exit 0
