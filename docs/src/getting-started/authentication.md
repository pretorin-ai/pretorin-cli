# Authentication

## Getting an API Key

Get your API key from [platform.pretorin.com](https://platform.pretorin.com/).

> **Beta Note:** Framework and control browsing works for authenticated users. Platform write features (evidence, narratives, monitoring) require a beta code. Systems can only be created on the platform, not through the CLI or MCP. [Sign up for early access](https://pretorin.com/early-access/).

All hosted API access is account-scoped and authenticated. Access to Pretorin-hosted services and any returned account-scoped data is governed by the applicable platform terms in addition to the open-source license for this repository.

## Login

```bash
pretorin login
```

Options:

| Flag | Description |
|------|-------------|
| `--api-key`, `-k` | API key (will prompt if not provided) |
| `--api-url` | Custom API base URL (for self-hosted instances) |

You'll be prompted to enter your API key. Credentials are stored in `~/.pretorin/config.json`.

If you're already authenticated, `pretorin login` validates your existing key against the API and skips the prompt. To re-authenticate with a different key, pass it explicitly:

```bash
pretorin login --api-key <new-key>
```

If you log into a different API endpoint or switch API keys, Pretorin clears the stored active `system + framework` context so stale scope does not bleed into the new environment.

## Verify Authentication

```bash
$ pretorin whoami
╭──────────────────────────────── Your Session ────────────────────────────────╮
│ Status: Authenticated                                                        │
│ API Key: 4MAS****...9v7o                                                     │
│ API URL: https://platform.pretorin.com/api/v1/public                         │
│ Frameworks Available: 8                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

For machine-readable output, use the global `--json` flag:

```bash
pretorin --json whoami
```

## Logout

Clear stored credentials:

```bash
pretorin logout
```

## API Key via Environment Variable

You can set your API key via environment variable instead of `pretorin login`. The environment variable takes precedence over stored config:

```bash
export PRETORIN_API_KEY=pretorin_your_key_here
```

This is useful for CI/CD pipelines and containerized environments.
