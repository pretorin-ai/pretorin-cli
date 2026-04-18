#!/bin/bash
# Local CI check — runs the same checks as the GitHub Actions pipeline.
# Not enforced at commit time; run manually before pushing.
#
# Usage:
#   ./scripts/check.sh          # Run all checks
#   ./scripts/check.sh lint     # Ruff lint + format check
#   ./scripts/check.sh audit    # pip-audit dependency scan
#   ./scripts/check.sh typecheck # mypy strict type check
#   ./scripts/check.sh test     # pytest with coverage
#   ./scripts/check.sh quick    # lint + typecheck (no install, fast)

set -euo pipefail

cd "$(dirname "$0")/.."

# Use uv run to invoke tools when they aren't installed globally.
# If 'uv' is available, prefix tool commands with 'uv run'; otherwise call directly.
if command -v uv &>/dev/null; then
    RUN="uv run"
else
    RUN=""
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

passed=0
failed=0
skipped=0
failures=""

step() {
    echo ""
    echo -e "${BOLD}━━━ $1 ━━━${RESET}"
}

pass() {
    echo -e "${GREEN}✓ $1 passed${RESET}"
    ((++passed))
}

fail() {
    echo -e "${RED}✗ $1 failed${RESET}"
    ((++failed))
    failures="${failures}\n  - $1"
}

skip() {
    echo -e "${YELLOW}⊘ $1 skipped${RESET}"
    ((++skipped))
}

run_lint() {
    step "Lint (ruff)"
    if $RUN ruff check src/pretorin; then
        pass "ruff check"
    else
        fail "ruff check"
    fi

    if $RUN ruff format --check src/pretorin; then
        pass "ruff format"
    else
        fail "ruff format"
    fi
}

run_audit() {
    step "Dependency Audit (pip-audit)"
    if command -v pip-audit &>/dev/null; then
        if pip-audit --skip-editable . 2>&1; then
            pass "pip-audit"
        else
            fail "pip-audit"
        fi
    elif [ -n "$RUN" ] && $RUN python -c "import pip_audit" &>/dev/null 2>&1; then
        if $RUN pip-audit --skip-editable . 2>&1; then
            pass "pip-audit"
        else
            fail "pip-audit"
        fi
    else
        echo -e "${YELLOW}pip-audit not installed — run: pip install pip-audit${RESET}"
        skip "pip-audit"
    fi
}

run_typecheck() {
    step "Type Check (mypy)"
    if $RUN mypy src/pretorin; then
        pass "mypy"
    else
        fail "mypy"
    fi
}

run_test() {
    step "Tests (pytest)"
    if $RUN pytest -v --cov=pretorin --cov-report=term-missing --cov-fail-under=60; then
        pass "pytest"
    else
        fail "pytest"
    fi
}

summary() {
    echo ""
    echo -e "${BOLD}━━━ Summary ━━━${RESET}"
    echo -e "  ${GREEN}${passed} passed${RESET}  ${RED}${failed} failed${RESET}  ${YELLOW}${skipped} skipped${RESET}"
    if [ "$failed" -gt 0 ]; then
        echo -e "${RED}Failures:${failures}${RESET}"
        exit 1
    fi
}

case "${1:-all}" in
    lint)
        run_lint
        ;;
    audit)
        run_audit
        ;;
    typecheck)
        run_typecheck
        ;;
    test)
        run_test
        ;;
    quick)
        run_lint
        run_typecheck
        ;;
    all)
        run_lint
        run_audit
        run_typecheck
        run_test
        ;;
    *)
        echo "Usage: $0 {all|lint|audit|typecheck|test|quick}"
        exit 1
        ;;
esac

summary
