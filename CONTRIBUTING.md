# Contributing to Pretorin CLI

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
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
pytest
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

## Submitting Changes

1. Create a feature branch from `main`
2. Make your changes
3. Ensure tests pass and code is properly formatted
4. Submit a pull request

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- CLI version (`pretorin version`)

## Questions?

For questions about the API or platform, see [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs).
