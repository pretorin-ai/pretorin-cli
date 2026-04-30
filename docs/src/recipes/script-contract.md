# Script Contract

Every script declared under `scripts:` in `recipe.md` must export a single
async function:

```python
async def run(ctx, **params) -> dict:
    ...
```

That's the entire contract. The recipe runner imports the module, calls
`run`, awaits the result, and hands it back to the calling agent as the
MCP tool response.

## The Signature

```python
from typing import Any

async def run(ctx: Any, *, stig_id: str, target: str = "local") -> dict[str, Any]:
    """Run a baseline scan and return per-rule results."""
    ...
```

| Argument | Type | What it is |
|----------|------|------------|
| `ctx` | `RecipeScriptContext` | Per-invocation execution context (see below). |
| `**params` | varies | The keyword args the agent supplied, validated against `scripts.<name>.params` in the manifest. |

The function **must** be `async`. Use `await` for I/O. Pretorin's writer
tools are async; using sync HTTP or sync subprocess for slow operations
will block the recipe runner's event loop.

The return value **must** be a JSON-serializable `dict`. Anything with
`tuple`, `set`, `datetime`, or custom classes will fail to serialize back
through MCP.

## The `ctx` Argument

`RecipeScriptContext` (defined in `src/pretorin/recipes/runner.py`):

```python
@dataclass
class RecipeScriptContext:
    system_id: str | None
    framework_id: str | None
    api_client: Any           # PretorianClient — see writer-tools.md
    logger: logging.Logger
    recipe_id: str
    recipe_version: str
    recipe_context_id: str | None
```

The two you'll use most:

- **`ctx.api_client`** — the authenticated `PretorianClient`. Use this to
  call platform-API methods (`ctx.api_client.create_evidence(...)`,
  `ctx.api_client.get_test_manifest(...)`, etc.). See
  [Writer tools](./writer-tools.md) for the full surface.
- **`ctx.logger`** — a `logging.Logger` named for the recipe. Prefer this
  over `print` so the calling agent's logs stay structured.

`ctx.system_id` is set when the calling agent specified a system at
`pretorin_start_recipe` time. Use it for any per-system platform call. If
your recipe doesn't make sense without a system, raise early with a clear
error.

`ctx.recipe_context_id` is the active execution context id. The MCP write
handlers read it from the session automatically — you only need to pass
it explicitly if your script makes a platform write **outside** the MCP
boundary (e.g., a direct `httpx` call against a custom internal endpoint).

## Returning Results

Whatever your script returns becomes the MCP tool response the calling
agent reads. Keep it structured: nested dicts the agent can inspect, with
clear keys.

```python
async def run(ctx, *, stig_id: str) -> dict[str, Any]:
    rules = await fetch_rules(ctx.api_client, ctx.system_id, stig_id)
    results = await scan(rules)
    return {
        "stig_id": stig_id,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == "pass"),
            "failed": sum(1 for r in results if r.status == "fail"),
        },
        "rules": [r.to_dict() for r in results],
    }
```

Return shapes the agent can pattern-match are easier to act on than freeform
prose. Save the prose for the recipe body — let the script return data.

## Imports Inside `scripts/`

The runner adds the recipe's `scripts/` directory to `sys.path` for the
duration of the call, so a sibling module is reachable as a top-level
import:

```python
# scripts/run_scan.py
from helpers import normalize_results   # reaches scripts/helpers.py
```

The path is removed after the call returns. You don't have to
`__init__.py`-decorate the directory.

## Error Handling

Don't swallow exceptions inside `run`. Let them propagate — the runner
catches them, logs them, and returns a structured error to the calling
agent. Catching and returning a string error makes the agent think the
call succeeded.

```python
# Bad
async def run(ctx, *, stig_id: str) -> dict[str, Any]:
    try:
        return await fetch(ctx, stig_id)
    except Exception as e:
        return {"error": str(e)}        # agent sees a "successful" call

# Good
async def run(ctx, *, stig_id: str) -> dict[str, Any]:
    return await fetch(ctx, stig_id)    # exceptions surface as tool errors
```

## Patterns

Three shapes cover most recipes:

### Capture-from-source

The recipe pulls a thing (a config file, a snippet of code, a query
result), redacts it, and registers an evidence record.

```python
async def run(ctx, *, file_path: str, line_range: str | None = None) -> dict[str, Any]:
    text = (Path(file_path).read_text()).split("\n")
    snippet = _slice(text, line_range)
    redacted, summary = redact_secrets(snippet)
    composed = compose_audit_markdown(redacted, file_path=file_path, line_range=line_range)
    evidence_id = await ctx.api_client.create_evidence(
        system_id=ctx.system_id,
        ...
    )
    return {"evidence_id": evidence_id, "redaction_summary": summary.to_dict()}
```

### Wrap-a-scanner

The recipe wraps an external tool (oscap, inspec, az, aws), runs it
against the platform's test manifest, and returns per-rule results.

```python
async def run(ctx, *, stig_id: str, target: str = "local") -> dict[str, Any]:
    manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id=stig_id)
    rules = rules_for_stig(manifest, stig_id)
    scanner = InSpecScanner()
    results = await scanner.execute(rules, config={"target": target})
    return {
        "stig_id": stig_id,
        "summary": summarize_results(results),
    }
```

The five built-in scanner recipes are exactly this shape — each is a thin
adapter over a `pretorin.scanners.*` class.

### Q-and-A attestation

The recipe is the agent collecting human attestations interactively, with
no external tool involved. Inputs are structured answers; the recipe just
records them.

```python
async def run(ctx, *, stig_id: str, attestations: list[dict]) -> dict[str, Any]:
    scanner = ManualScanner()
    results = await scanner.execute(rules, config={"attestations": attestations})
    return {"stig_id": stig_id, "summary": summarize_results(results)}
```

## When to Write Multiple Scripts

If your recipe has steps that the calling agent might want to interleave
with reasoning (e.g., "redact, show me, then compose"), expose each step
as its own script. The agent can then call them as separate MCP tools and
inspect the intermediate output.

The `code-evidence-capture` recipe ships two scripts (`redact_secrets` and
`compose_snippet`) for exactly this reason.
