# Authentication

## Getting an API Key

Get your API key from [platform.pretorin.com](https://platform.pretorin.com/).

> **Beta Note:** Framework and control browsing works for authenticated users. Platform write features (evidence, narratives, monitoring) require a beta code. Systems can only be created on the platform, not through the CLI or MCP. [Sign up for early access](https://pretorin.com/early-access/).

All hosted API access is account-scoped and authenticated. Access to Pretorin-hosted services and any returned account-scoped data is governed by the applicable platform terms in addition to the open-source license for this repository.

## Login

```bash
pretorin login
```

You'll be prompted to enter your API key. Credentials are stored in `~/.pretorin/config.json`.

If you're already authenticated, `pretorin login` validates your existing key against the API and skips the prompt.

If you log into a different API endpoint or switch API keys, Pretorin clears the stored active `system + framework` context so stale scope does not bleed into the new environment.

## Verify Authentication

```bash
$ pretorin whoami
[°~°] Checking your session...
╭──────────────────────────────── Your Session ────────────────────────────────╮
│ Status: Authenticated                                                        │
│ API Key: 4MAS****...9v7o                                                     │
│ API URL: https://platform.pretorin.com/api/v1                                │
│ Frameworks Available: 8                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
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
