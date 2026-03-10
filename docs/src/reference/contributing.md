# Contributing

Thank you for your interest in contributing to the Pretorin CLI!

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pretorin-cli.git
   cd pretorin-cli
   ```
3. Install development dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
pytest
```

Integration tests require an API key and are marked with `@pytest.mark.integration`:

```bash
pytest -m integration
```

### Type Checking

```bash
mypy src/pretorin
```

### Linting

```bash
ruff check src/pretorin
ruff format src/pretorin
```

### Full CI Check

Run the same checks as the CI pipeline:

```bash
ruff check src/pretorin && ruff format --check src/pretorin && mypy src/pretorin && pytest
```

## Submitting Changes

1. Create a feature branch from `master`
2. Make your changes
3. Ensure tests pass and code is properly formatted
4. Submit a pull request

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

## CI Pipeline

The CI pipeline runs on Python 3.10, 3.11, and 3.12:

- **Lint** — Ruff check + format
- **Audit** — pip-audit (dependency vulnerability scan)
- **Type check** — mypy strict mode
- **Test** — pytest

## Reporting Issues

Use [GitHub Issues](https://github.com/pretorin-ai/pretorin-cli/issues) to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- CLI version (`pretorin version`)

## Questions?

- API documentation: [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs)
- Platform: [platform.pretorin.com](https://platform.pretorin.com)
