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
```

## Show Current Context

```bash
$ pretorin context show
╭──────────────────────── Active Context ─────────────────────────╮
│ System: My Application                                          │
│ Framework: NIST SP 800-53 Rev 5                                │
│ Progress: 42% (136/324 implemented, 45 in progress)            │
╰─────────────────────────────────────────────────────────────────╯
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
