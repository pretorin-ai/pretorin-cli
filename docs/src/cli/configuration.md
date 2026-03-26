# Configuration

The `config` command group manages CLI configuration stored at `~/.pretorin/config.json`.

## List Configuration

```bash
$ pretorin config list
          Pretorin Configuration
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Key     ┃ Value           ┃ Source      ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ api_key │ 4MAS****...9v7o │ config file │
└─────────┴─────────────────┴─────────────┘

Config file: /home/user/.pretorin/config.json
```

## Get a Config Value

```bash
pretorin config get api_key
```

## Set a Config Value

```bash
pretorin config set api_base_url https://custom-api.example.com/api/v1
```

## Show Config File Path

```bash
$ pretorin config path
/home/user/.pretorin/config.json
```

## Config File Format

The config file is JSON:

```json
{
  "api_key": "pretorin_...",
  "api_base_url": "https://platform.pretorin.com/api/v1/public",
  "model_api_base_url": "https://platform.pretorin.com/api/v1/public/model",
  "active_system": "My Application",
  "active_framework": "nist-800-53-r5",
  "disable_update_check": false
}
```

## Configuration Keys

| Key | Description |
|-----|-------------|
| `api_key` | Pretorin API key |
| `api_base_url` | Platform REST API URL |
| `model_api_base_url` | Model API URL for agent runtime |
| `openai_api_key` | Optional model key for agent runtime |
| `active_system` | Currently active system name |
| `active_framework` | Currently active framework ID |
| `disable_update_check` | Disable passive update notifications |

## Environment Variable Overrides

Environment variables take precedence over config file values. See [Environment Variables](../reference/environment.md) for the full list.
