# Environment Variables

Environment variables override stored configuration values.

## Authentication & API

| Variable | Description | Default |
|----------|-------------|---------|
| `PRETORIN_API_KEY` | API key for platform access. Overrides `api_key` in config file. | — |
| `PRETORIN_PLATFORM_API_BASE_URL` | Platform REST API base URL | `https://platform.pretorin.com/api/v1/public` |
| `PRETORIN_API_BASE_URL` | Backward-compatible alias for `PRETORIN_PLATFORM_API_BASE_URL` | — |
| `PRETORIN_MODEL_API_BASE_URL` | Model API URL for agent runtime | `https://platform.pretorin.com/v1` |

## Agent Runtime

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Model key override for agent runtime. Takes precedence over stored Pretorin login key. | — |

## Behavior

| Variable | Description | Default |
|----------|-------------|---------|
| `PRETORIN_DISABLE_UPDATE_CHECK` | Set to `1` to disable passive update notifications | — |
| `PRETORIN_LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `WARNING` |

## Precedence

For the API key:
1. `PRETORIN_API_KEY` environment variable (highest)
2. `api_key` in `~/.pretorin/config.json`

For the model key (agent runtime):
1. `OPENAI_API_KEY` environment variable (highest)
2. `config.api_key` (from `pretorin login`)
3. `config.openai_api_key`

## CI/CD Example

```bash
export PRETORIN_API_KEY=pretorin_your_key_here
export PRETORIN_DISABLE_UPDATE_CHECK=1

pretorin frameworks list
pretorin evidence push
```
