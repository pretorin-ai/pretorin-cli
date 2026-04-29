# STIG Scanning

> **Note**: The legacy `pretorin scan` command was removed when the recipes
> system landed. Scanning now happens through **recipes**: each scanner ships
> as a built-in recipe that the calling AI agent (Claude Code, Codex CLI,
> custom MCP client, or `pretorin agent`) invokes through MCP.
>
> If you have local automation that called `pretorin scan run`, switch it to
> invoke the recipe directly via the agent or use `pretorin recipe list` to
> discover the equivalent recipe.

## Available Scanner Recipes

| Recipe ID | Wraps | CLI requirement |
|-----------|-------|-----------------|
| `inspec-baseline` | Chef InSpec | `inspec` |
| `openscap-baseline` | OpenSCAP | `oscap` |
| `cloud-aws-baseline` | AWS APIs (boto3) | `aws` |
| `cloud-azure-baseline` | Azure APIs | `az` |
| `manual-attestation` | Human attestation (no external tool) | — |

List them locally:

```bash
pretorin recipe list
pretorin recipe show inspec-baseline
```

## How a Calling Agent Runs a Scan

The agent (running in your IDE or via `pretorin agent run`) opens a recipe
context, calls the recipe's `run_scan` script with a STIG id, and submits the
returned per-rule results to the platform via `pretorin_submit_test_results`.

The recipe body (the markdown under the frontmatter in `recipe.md`) is the
prompt the agent reads to know what to do. You don't run the recipe by hand;
you ask the agent something like:

> "Run an inspec-baseline scan against `RHEL_9_STIG` on this system."

Behind the scenes the agent:

1. Calls `pretorin_start_recipe(id="inspec-baseline", system_id=...)`.
2. Calls the recipe's `run_scan` tool with `stig_id="RHEL_9_STIG"`.
3. Reads the returned summary (per-rule pass/fail/error/not_applicable counts).
4. Submits results via `pretorin_submit_test_results`.
5. Calls `pretorin_end_recipe(...)`.

## Test Manifest

Browse what's testable for a system without running anything:

```bash
pretorin stig applicable --system "My System"
pretorin cci chain ac-2 --system "My System"
```

The MCP equivalent is `pretorin_get_test_manifest` — the calling agent uses
this to figure out which rules apply before running a scan.

## Authoring Your Own Scanner Recipe

Scanner recipes are just recipes. If you have an internal tool that produces
STIG-style results, scaffold a recipe and drop it in
`~/.pretorin/recipes/<id>/` (user) or `<repo>/.pretorin/recipes/<id>/` (team):

```bash
pretorin recipe new my-scanner --user
```

See the [Authoring recipes](../recipes/index.md) docs for the full contract.

## Submitting Results Manually

If you have raw scan output and want to push it without running the recipe
flow, the platform endpoint is exposed directly:

```
pretorin_submit_test_results(system_id, results)
```

via MCP. Each result needs `rule_id`, `benchmark_id`, `status`, and tool
metadata — see the [STIG / CCI workflow](../workflows/stig-scanning.md) for
schema details.
