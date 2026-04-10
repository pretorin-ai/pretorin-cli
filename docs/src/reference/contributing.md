# Contributing

Thank you for your interest in contributing to the Pretorin CLI!

We welcome contributions to the CLI, MCP server, docs, scanners, developer workflows, and local tooling. This repository is open source under Apache-2.0, while Pretorin-hosted platform services, authenticated API access, and account-scoped data are governed separately by the applicable platform terms.

## Scope

Good fits for this repository:

- CLI commands and output improvements
- MCP tools, prompts, and local agent integrations
- Scanner integrations and developer workflow automation
- Documentation, examples, and tests

Out of scope for public contributions:

- Customer data, exported platform data, or private operational runbooks
- Secrets, internal credentials, or private environment details
- Changes that imply trademark rights or suggest an unofficial fork is an official Pretorin service

For brand usage guidance, see [Trademarks and Service Terms](./trademarks.md).

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

Integration tests require a valid API key tied to an account that has accepted the platform terms.

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

1. Create a feature branch from `main`
2. Make your changes
3. Ensure tests pass and code is properly formatted
4. Add a sign-off to each commit with `git commit -s`
5. Submit a pull request

By submitting a contribution, you certify that:

- You have the right to submit the code, docs, or other materials.
- Your contribution may be distributed under the Apache License, Version 2.0.
- You are not including confidential information, customer data, or material that is governed by separate platform terms.

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

## Legal and Platform Boundaries

- The source code in this repository is licensed under Apache-2.0.
- The Pretorin name, logos, and other brand assets remain subject to trademark rights and are not licensed for reuse except for nominative/reference use. See [Trademarks and Service Terms](./trademarks.md).
- Access to Pretorin-hosted APIs, services, and account-scoped data is authenticated and governed by separate platform terms.

## Reporting Issues

Use [GitHub Issues](https://github.com/pretorin-ai/pretorin-cli/issues) to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- CLI version (`pretorin version`)

## Questions?

- API documentation: [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs)
- Platform: [platform.pretorin.com](https://platform.pretorin.com)
