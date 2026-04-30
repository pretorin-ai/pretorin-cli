# Worked Example: a Community Recipe

This walkthrough builds a community recipe end-to-end, the same way you
would. The recipe captures the most recent N entries from a structured
audit log file as evidence for an access-control review.

The recipe doesn't ship with pretorin-cli — it's a teaching artifact.
Drop it under `~/.pretorin/recipes/audit-log-capture/` to actually run
it; the files are reproduced below for reference.

## What This Recipe Does

The audit team needs evidence that an admin's recent actions are being
logged. They have a structured log file (one JSON event per line). The
recipe:

1. Reads the last N entries from the log.
2. Filters to events matching a username.
3. Composes a markdown evidence body with the events as a code block.
4. Returns the composed text to the calling agent so the agent can hand
   it to `pretorin_create_evidence`.

The recipe doesn't write evidence itself — it returns structured data the
agent submits through the MCP write boundary. That's where audit metadata
gets stamped automatically.

## Directory Layout

```
~/.pretorin/recipes/audit-log-capture/
├── recipe.md
├── README.md
└── scripts/
    └── capture.py
```

## `recipe.md`

```markdown
---
id: audit-log-capture
version: 0.1.0
name: "Audit Log Capture"
description: "Capture the most recent admin events from a JSONL audit log and return a formatted markdown body for evidence submission."
use_when: "The auditor needs evidence that admin actions are logged. You have a JSONL audit log file path and a username to filter on."
produces: evidence
author: "Example Team"
license: Apache-2.0
attests:
  - { control: AU-2, framework: nist-800-53-r5 }
  - { control: AU-3, framework: nist-800-53-r5 }
params:
  log_path:
    type: string
    description: "Absolute path to the JSONL audit log file"
    required: true
  username:
    type: string
    description: "Admin username to filter events for"
    required: true
  limit:
    type: integer
    description: "Maximum number of events to include"
    default: 20
scripts:
  capture:
    path: scripts/capture.py
    description: "Read the audit log, filter by username, return composed markdown."
    params:
      log_path:
        type: string
        description: "Absolute path to JSONL log"
        required: true
      username:
        type: string
        description: "Admin username"
        required: true
      limit:
        type: integer
        description: "Max events"
        default: 20
---

# Audit Log Capture

Reads the tail of a JSONL audit log, filters to events for one admin
user, and returns a composed markdown body the calling agent can submit
as a configuration evidence record.

The agent should attach the result to the relevant `AU-2` / `AU-3`
implementation narrative for the system.
```

## `scripts/capture.py`

```python
"""Capture recent audit events for a specific admin user."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pretorin.evidence.markdown import compose


async def run(
    ctx: Any,
    *,
    log_path: str,
    username: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Read tail of JSONL log, filter to one user, compose evidence body."""
    path = Path(log_path)
    if not path.is_file():
        raise FileNotFoundError(f"audit log not found: {log_path}")

    matched: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("user") == username:
            matched.append(event)
        if len(matched) >= limit:
            break

    snippet = "\n".join(json.dumps(e, sort_keys=True) for e in matched)
    body = compose(
        prose=(
            f"The {len(matched)} most recent audit events for user "
            f"{username!r} from {path.name}. Each line is one structured "
            "event (timestamp, action, target, source IP)."
        ),
        snippet=snippet,
        snippet_lang="json",
        file_path=str(path),
    )
    return {
        "username": username,
        "event_count": len(matched),
        "evidence_body": body,
    }
```

## `README.md`

```markdown
# audit-log-capture

A community recipe that captures admin audit events as markdown evidence.

## Try it

1. Drop this directory under ~/.pretorin/recipes/audit-log-capture/
2. Run `pretorin recipe validate audit-log-capture`
3. From your AI agent (Claude Code, Codex CLI), ask:
   > "Capture the last 20 audit events for admin alice from /var/log/audit.jsonl
   > as evidence for AU-2."
```

## Walking Through It

### Why split into manifest + script

Everything inside the frontmatter is **what the calling agent reads** to
decide *whether* to use the recipe. Everything in `scripts/capture.py` is
*how* the work happens. Keep the description sharp — the agent picks based
on it.

### Why use `compose` from `pretorin.evidence.markdown`

`compose` produces an audit-grade markdown body: prose explaining the
context, a fenced code block with the snippet, an italic provenance
footer with the file path and timestamp. Doing this by hand drifts; using
the helper keeps every evidence record consistent.

### Why no `create_evidence` call

The recipe returns the composed body and lets the calling agent submit it
via `pretorin_create_evidence`. This is the right shape for two reasons:

1. **Audit metadata gets stamped at the MCP write boundary.** The recipe
   context is open in the calling agent's session; routing through MCP
   means the handler reads the context and stamps `producer_kind="recipe"`
   automatically.
2. **The agent stays in the loop.** The agent can review the composed
   body, ask the user to confirm before submitting, or attach extra
   metadata it pulled from elsewhere.

A recipe that takes raw input and produces structured output the agent
hands to a writer tool is the most useful shape. Recipes that perform
their own writes are sometimes appropriate (the scanner recipes do, via
`submit_test_results`) but the default should be: return data, let the
agent submit.

### How the agent invokes it

The MCP tool name is `pretorin_recipe_audit_log_capture__capture` (the
hyphens in the recipe id become underscores; the script name is the
suffix after `__`).

The agent's call sequence:

```
pretorin_start_recipe(id="audit-log-capture", version="0.1.0",
                      params={"log_path": "/var/log/audit.jsonl",
                              "username": "alice", "limit": 20})
  → returns context_id

pretorin_recipe_audit_log_capture__capture(
    log_path="/var/log/audit.jsonl",
    username="alice",
    limit=20,
)
  → returns {"username": "alice", "event_count": 20, "evidence_body": "..."}

pretorin_create_evidence(
    system_id="...",
    control_id="au-2",
    framework_id="nist-800-53-r5",
    name="Recent admin audit events for alice",
    evidence_type="configuration",
    description=<the evidence_body from the previous call>,
    recipe_context_id=<context_id>,
)
  → platform stamps producer_kind="recipe", producer_id="audit-log-capture",
                    producer_version="0.1.0"

pretorin_end_recipe(context_id=<context_id>, status="pass")
```

### What the agent should not do

The recipe doesn't include a `submit` script that calls
`create_evidence` directly. Why: every evidence record submitted from
inside the recipe context picks up audit metadata at the MCP boundary;
moving the write into the script would require the script to build
metadata itself, which is one more place for the audit trail to drift.

When in doubt, **return data, let the agent write**.
