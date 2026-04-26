# Context Management

The `context` command group manages your active system and framework scope. Platform-backed compliance operations (evidence, narratives, notes, monitoring, control status) run inside exactly one `system + framework` pair at a time.

This works similarly to `kubectl config use-context` — set your scope once, then run commands within it.

## List Available Systems

```bash
$ pretorin context list
[°~°] Fetching your systems...
                              Your Systems
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ System           ┃ Framework ID       ┃ Progress % ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ My Application   │ nist-800-53-r5     │        42% │ in_progress │
│ My Application   │ fedramp-moderate   │        28% │ in_progress │
│ Internal Tool    │ cmmc-l2            │        75% │ implemented │
└──────────────────┴────────────────────┴────────────┴───────────┘
```

## Set Active Context

```bash
# Interactive — prompts for system and framework selection
pretorin context set

# Explicit
pretorin context set --system "My Application" --framework nist-800-53-r5

# Skip automatic source verification after setting context
pretorin context set --system "My Application" --framework nist-800-53-r5 --no-verify
```

| Option | Description |
|--------|-------------|
| `--system` / `-s` | System name or ID |
| `--framework` / `-f` | Framework ID (e.g., `fedramp-moderate`) |
| `--no-verify` | Skip source verification after setting context |

Pretorin stores the canonical system ID for stability and also caches the last known system name for display. After setting context, source verification runs automatically unless `--no-verify` is passed. If you change API keys or platform endpoints with `pretorin login`, the stored active context is cleared automatically so old scope does not leak into the new environment.

## Show Current Context

```bash
$ pretorin context show
╭──────────────────────── Active Context ─────────────────────────╮
│ System: My Application (sys-1234...)                           │
│ Framework: nist-800-53-r5                                      │
│ Progress: 42%                                                  │
│ Status: in_progress                                            │
╰─────────────────────────────────────────────────────────────────╯

# Compact summary for shell use
pretorin context show --quiet

# Fail fast if the stored context is missing, stale, or cannot be verified
pretorin context show --quiet --check
```

`context show` validates the stored system and framework against the platform when credentials are available. If the system has been deleted or the framework is no longer attached, the command reports that state explicitly instead of silently showing a stale context.

## Verify Context

Verify the active context against source attestation:

```bash
# Full output
pretorin context verify

# Compact output with custom TTL
pretorin context verify --ttl 7200 --quiet
```

| Option | Description |
|--------|-------------|
| `--ttl` | Verification TTL in seconds (default: 3600) |
| `--quiet` / `-q` | Compact output |

## Source Manifest

Show the resolved source manifest and evaluate it against detected sources:

```bash
pretorin context manifest
pretorin context manifest --quiet
```

## Clear Context

```bash
pretorin context clear
```

## Single-Scope Enforcement

All platform write operations must target exactly one system + framework pair. This includes:

- Evidence creation and push
- Narrative updates
- Control notes
- Monitoring events
- Control status updates

If you need to work across multiple frameworks (e.g., `fedramp-low` and `fedramp-moderate`), run them as separate operations:

```bash
# Work on FedRAMP Moderate
pretorin context set --system "My App" --framework fedramp-moderate
pretorin evidence push

# Switch to FedRAMP Low
pretorin context set --system "My App" --framework fedramp-low
pretorin evidence push
```

Some commands also accept explicit `--system` and `--framework` flags, which override the stored context for that invocation.
