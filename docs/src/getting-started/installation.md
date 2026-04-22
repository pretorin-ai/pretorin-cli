# Installation

Pretorin CLI requires Python 3.10 or later.

## Recommended: uv

[uv](https://docs.astral.sh/uv/) installs the CLI as an isolated tool with its own dependencies:

```bash
uv tool install pretorin
```

## pip

```bash
pip install pretorin
```

## pipx

[pipx](https://pipx.pypa.io/) provides isolated installation similar to uv:

```bash
pipx install pretorin
```

## Docker

A Dockerfile and Docker Compose configuration are included in the repository:

```bash
git clone https://github.com/pretorin-ai/pretorin-cli.git
cd pretorin-cli
docker compose up
```

## Verify Installation

```bash
pretorin version
```

Expected output:

```
pretorin version 0.16.1
```

## Updating

Check for and install the latest version:

```bash
pretorin update
```

The CLI also checks for updates automatically on startup and notifies you when a new version is available. To disable passive update notifications:

```bash
export PRETORIN_DISABLE_UPDATE_CHECK=1
# or
pretorin config set disable_update_check true
```

## Development Installation

For contributing to Pretorin CLI:

```bash
git clone https://github.com/pretorin-ai/pretorin-cli.git
cd pretorin-cli
uv pip install -e ".[dev]"
```

This installs the package in editable mode with development dependencies (pytest, ruff, mypy, etc.).
