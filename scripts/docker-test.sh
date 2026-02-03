#!/bin/bash
# Convenience script for running containerized tests
# Usage:
#   ./scripts/docker-test.sh           # Run all tests
#   ./scripts/docker-test.sh lint      # Run linter only
#   ./scripts/docker-test.sh typecheck # Run type checker only
#   ./scripts/docker-test.sh coverage  # Run tests with coverage
#   ./scripts/docker-test.sh all       # Run lint, typecheck, and tests

set -e

cd "$(dirname "$0")/.."

case "${1:-test}" in
    test)
        echo "Running tests..."
        docker-compose run --rm test
        ;;
    lint)
        echo "Running linter..."
        docker-compose run --rm lint
        ;;
    typecheck)
        echo "Running type checker..."
        docker-compose run --rm typecheck
        ;;
    coverage)
        echo "Running tests with coverage..."
        docker-compose run --rm test-coverage
        ;;
    integration)
        if [ -z "$PRETORIN_API_KEY" ]; then
            echo "Error: PRETORIN_API_KEY environment variable is required for integration tests"
            exit 1
        fi
        echo "Running integration tests..."
        docker-compose run --rm integration
        ;;
    all)
        echo "Running lint..."
        docker-compose run --rm lint
        echo ""
        echo "Running type checker..."
        docker-compose run --rm typecheck
        echo ""
        echo "Running tests..."
        docker-compose run --rm test
        echo ""
        echo "All checks passed!"
        ;;
    *)
        echo "Usage: $0 {test|lint|typecheck|coverage|integration|all}"
        exit 1
        ;;
esac
