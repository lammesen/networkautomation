#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
CONTENT=$(echo "$INPUT" | jq -r '.tool_input.content // ""')

[[ -z "$FILE_PATH" ]] && exit 0

PROTECTED_PATTERNS=("\.env$" "\.env\." "\.pem$" "\.key$" "\.p12$" "credentials" "secrets\.yaml" "secrets\.yml" "\.git/" "node_modules/" "__pycache__/" "\.pyc$" "venv/" "\.venv/" "staticfiles/")
for pattern in "${PROTECTED_PATTERNS[@]}"; do
    if echo "$FILE_PATH" | grep -qE "$pattern"; then
        echo "❌ Protected file: $FILE_PATH" >&2
        exit 2
    fi
done

if [[ -n "$CONTENT" && "$TOOL_NAME" == "Write" ]]; then
    echo "$CONTENT" | grep -qE "AKIA[0-9A-Z]{16}" && { echo "❌ Possible AWS key" >&2; exit 2; }
    echo "$CONTENT" | grep -qE "sk-[a-zA-Z0-9]{32,}" && { echo "❌ Possible OpenAI key" >&2; exit 2; }
    echo "$CONTENT" | grep -qE "ghp_[a-zA-Z0-9]{36}" && { echo "❌ Possible GitHub token" >&2; exit 2; }
    if echo "$CONTENT" | grep -qiE "(password|secret|api_key|apikey|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]" && ! echo "$CONTENT" | grep -qE "(os\.environ|getenv|settings\.|config\.)"; then
        echo "⚠️ Credential-like assignment" >&2
    fi
fi

if [[ "$FILE_PATH" =~ backend/webnet/.*\.py$ && -n "$CONTENT" ]]; then
    echo "$CONTENT" | grep -qE "\.raw\(|\.execute\(|cursor\." && echo "⚠️ Raw SQL in $FILE_PATH" >&2
    if echo "$CONTENT" | grep -qE "class.*ViewSet.*:" && ! echo "$CONTENT" | grep -qE "permission_classes\s*="; then
        echo "⚠️ ViewSet missing permission_classes" >&2
    fi
    if echo "$CONTENT" | grep -qE "customer\s*=\s*models\.ForeignKey" && ! echo "$CONTENT" | grep -qE "CustomerScopedQuerysetMixin|filter.*customer"; then
        echo "⚠️ Customer FK may need tenant filtering" >&2
    fi
fi

if [[ "$FILE_PATH" =~ \.(ts|tsx)$ && -n "$CONTENT" ]]; then
    echo "$CONTENT" | grep -qE ": any\b|as any\b" && echo "⚠️ TypeScript any detected" >&2
    echo "$CONTENT" | grep -q "dangerouslySetInnerHTML" && echo "⚠️ dangerouslySetInnerHTML present" >&2
fi

exit 0
