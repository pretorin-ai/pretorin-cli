# Multi-stage Dockerfile for Pretorin CLI
# Supports: test, lint, and production targets

# =============================================================================
# Base stage - common dependencies
# =============================================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e .

# =============================================================================
# Test stage - includes dev dependencies for testing
# =============================================================================
FROM base AS test

# Install dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy test files
COPY tests/ ./tests/

# Default command runs pytest
CMD ["pytest", "-v"]

# =============================================================================
# Lint stage - for code quality checks
# =============================================================================
FROM base AS lint

# Install dev dependencies (includes ruff and mypy)
RUN pip install --no-cache-dir -e ".[dev]"

# Copy all source for linting
COPY tests/ ./tests/

# Default command runs ruff check
CMD ["ruff", "check", "src/pretorin"]

# =============================================================================
# Production stage - minimal image for running the CLI
# =============================================================================
FROM base AS production

# Create non-root user
RUN useradd --create-home --shell /bin/bash pretorin
USER pretorin

# Set up config directory
RUN mkdir -p /home/pretorin/.pretorin

ENTRYPOINT ["pretorin"]
CMD ["--help"]
