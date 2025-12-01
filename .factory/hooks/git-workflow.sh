#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

cd "$CWD"

if [[ "$TOOL_NAME" != "Execute" ]] || ! echo "$COMMAND" | grep -qE "^git "; then exit 0; fi

if echo "$COMMAND" | grep -qE "^git commit"; then
    PROTECTED_BRANCHES=("main" "master" "production" "prod")
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")
    for branch in "${PROTECTED_BRANCHES[@]}"; do
        if [[ "$CURRENT_BRANCH" == "$branch" ]]; then
            echo "❌ No commits on protected branch $branch; create a feature branch" >&2
            exit 2
        fi
    done
fi

if echo "$COMMAND" | grep -qE "^git commit.*-m"; then
    COMMIT_MSG=$(echo "$COMMAND" | sed -E 's/.*git commit.*-m[= ]*["'"'']([^"'"'']+)["'"''].*/\1/' || echo "")
    if [[ -n "$COMMIT_MSG" && ! "$COMMIT_MSG" =~ ^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.*\))?:.+ ]]; then
        echo "⚠️ Use Conventional Commits: type(scope): description" >&2
    fi
fi

if echo "$COMMAND" | grep -qE "^git checkout -b"; then
    BRANCH_NAME=$(echo "$COMMAND" | sed -E 's/.*git checkout -b[= ]*([^ ]+).*/\1/')
    if ! echo "$BRANCH_NAME" | grep -qE "^(feature|fix|hotfix|docs|refactor|chore)/[a-z0-9-]+$"; then
        echo "⚠️ Branch pattern: type/description (e.g., feature/add-device-tags)" >&2
    fi
fi

if echo "$COMMAND" | grep -qE "^git push"; then
    if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
        echo "⚠️ Uncommitted changes present before push" >&2
    fi
    if git grep -qE "^(<<<<<<<|=======|>>>>>>>)" 2>/dev/null; then
        echo "❌ Resolve merge conflict markers before push" >&2
        git grep -l "^(<<<<<<<|=======|>>>>>>>)" 2>/dev/null | head -5 >&2
        exit 2
    fi
fi

if echo "$COMMAND" | grep -qE "^git push.*(-f|--force)"; then
    echo "⚠️ Force push detected; ensure it's intentional" >&2
fi

exit 0
