# Monitoring Commands

The `monitoring` command group records security and compliance events against a system.

## Push a Monitoring Event

```bash
pretorin monitoring push --system "My System" --title "Quarterly Access Review" \
  --event-type access_review --severity info
```

## Event Types

| Type | Description |
|------|-------------|
| `security_scan` | Automated security scan result |
| `configuration_change` | Infrastructure or application configuration change |
| `access_review` | Periodic access review or audit |
| `compliance_check` | Compliance posture check or assessment |

## Severity Levels

| Severity | Description |
|----------|-------------|
| `critical` | Requires immediate attention |
| `high` | Significant finding |
| `medium` | Moderate finding |
| `low` | Minor finding |
| `info` | Informational event |

## Context Requirement

The `monitoring push` command requires an active system context. Set it with `pretorin context set` or pass `--system` explicitly.
