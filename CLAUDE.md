# Pretorin CLI — Claude Code Instructions

## Quick Reference

- **Main branch**: `master`
- **Language**: Python 3.10+, managed with `uv`
- **Docs**: mdBook (`docs/src/` → `docs/book/`, committed)

## Dev Setup

```bash
uv pip install -e ".[dev]"
```

## Commands

```bash
# Tests
pytest                          # unit tests (60% coverage minimum)
pytest --cov=pretorin           # with coverage
pytest -m integration           # integration tests (needs PRETORIN_API_KEY)

# Lint + type check
ruff check src/pretorin
ruff format --check src/pretorin
mypy src/pretorin

# All-in-one
./tools/check.sh quick        # lint + typecheck + tests
```

## Version Bumps

Three files must stay in sync:
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `src/pretorin/__init__.py` → `__version__ = "X.Y.Z"`
3. `CHANGELOG.md` + `docs/src/reference/changelog.md` (add entry + compare link)

Also update `docs/src/getting-started/installation.md` (expected output example).

## Docs Build

```bash
./tools/build-docs.sh
```

Rebuild and commit `docs/book/` whenever doc sources change — CI diffs the output. The Rust toolchain is pinned to 1.94.1 for deterministic search index hashes.

## Release Process

1. Bump version (see above)
2. Rebuild docs, commit everything
3. Merge to `master`
4. `git tag vX.Y.Z && git push origin vX.Y.Z`
5. `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."`
6. The `publish.yml` workflow automatically publishes to PyPI and the MCP Registry — the tag must match the package version

## Project Layout

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines and [docs/](docs/src/) for full documentation.
