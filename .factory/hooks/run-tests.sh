#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
cd "$CWD"

if [[ -z "$FILE_PATH" || ! "$TOOL_NAME" =~ ^(Write|Edit)$ ]]; then exit 0; fi
if [[ "$FILE_PATH" =~ (test_.*\.py|.*_test\.py|\.(test|spec)\.(ts|tsx|js|jsx)$) ]]; then exit 0; fi
if ! [[ "$FILE_PATH" =~ \.(py|ts|tsx|js|jsx)$ ]]; then exit 0; fi

if [[ "$FILE_PATH" =~ backend/webnet/.*\.py$ ]]; then
    FILENAME=$(basename "$FILE_PATH" .py)
    APP_NAME=$(echo "$FILE_PATH" | sed -E 's|backend/webnet/([^/]+)/.*|\1|')
    TEST_FILE="backend/webnet/tests/test_${FILENAME}.py"
    ALT_TEST_FILE="backend/webnet/${APP_NAME}/tests/test_${FILENAME}.py"
    TARGET=""
    [[ -f "$TEST_FILE" ]] && TARGET="$TEST_FILE"
    [[ -z "$TARGET" && -f "$ALT_TEST_FILE" ]] && TARGET="$ALT_TEST_FILE"
    if [[ -n "$TARGET" && -x backend/venv/bin/pytest ]]; then
        echo "🧪 Running $TARGET for $FILE_PATH..."
        (cd backend && ../backend/venv/bin/python -m pytest "$TARGET" -v --tb=short 2>&1 || echo "⚠️ Tests failed" >&2)
    elif [[ "$FILE_PATH" =~ (views|viewsets|serializers|services|repositories)\.py$ ]]; then
        echo "⚠️ No test file found for $FILE_PATH" >&2
    fi
fi

if [[ "$FILE_PATH" =~ backend/static/src/.*\.(ts|tsx)$ ]]; then
    TEST_FILE=$(echo "$FILE_PATH" | sed -E 's/\.(ts|tsx)$/.test.\1/')
    if [[ -f "$TEST_FILE" && -f backend/node_modules/.bin/vitest ]]; then
        echo "🧪 Running $TEST_FILE for $FILE_PATH..."
        (cd backend && node_modules/.bin/vitest run "$TEST_FILE" --reporter=dot 2>&1 || echo "⚠️ Tests failed" >&2)
    elif [[ "$FILE_PATH" =~ components/ && ! "$FILE_PATH" =~ /ui/ ]]; then
        echo "⚠️ No test file found for component: $FILE_PATH" >&2
    fi
fi

if [[ "${DROID_CHECK_COVERAGE:-false}" == "true" && "$FILE_PATH" =~ backend/webnet/.*\.py$ && -x backend/venv/bin/pytest ]]; then
    echo "📊 Checking coverage..."
    COVERAGE=$(cd backend && ../backend/venv/bin/python -m pytest --cov=webnet --cov-report=term-missing 2>/dev/null | grep TOTAL | awk '{print $NF}' | tr -d '%' || echo "")
    if [[ -n "$COVERAGE" && "$COVERAGE" -lt 70 ]]; then echo "⚠️ Coverage ${COVERAGE}% (<70%)"; else echo "✓ Coverage ${COVERAGE}%"; fi
fi

exit 0
