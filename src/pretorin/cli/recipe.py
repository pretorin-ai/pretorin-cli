"""``pretorin recipe`` CLI commands.

Phase A2 of the recipe-implementation design: the user-facing surface that
unblocks the contributor workflow. ``pretorin recipe new`` scaffolds a recipe,
``pretorin recipe validate`` checks it, ``pretorin recipe list / show`` are the
read-side surface over the registry. ``pretorin recipe run`` (Phase B2) is
the local-testing entry point so a contributor can exercise their recipe
without going through an external agent's MCP boundary.

Per the design's "Extensibility — Community Contribution Surface" section,
``pretorin recipe new`` defaults to ``--location user`` so a contributor can
ship their first recipe without a fork.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.recipes.context import get_default_store
from pretorin.recipes.errors import RecipeContextError, RecipeManifestError
from pretorin.recipes.loader import load_explicit_path
from pretorin.recipes.manifest import RecipeManifest
from pretorin.recipes.registry import RecipeRegistry
from pretorin.recipes.runner import RecipeScriptContext, run_script

app = typer.Typer(
    name="recipe",
    help="List, show, scaffold, and validate Pretorin recipes.",
    no_args_is_help=True,
)
console = Console()


# =============================================================================
# Scaffolder templates — embedded so `pretorin recipe new` works without
# needing a separate _templates/ data directory at install time. WS7 (the
# contributor-surface workstream) may move these into _templates/ once the
# scaffold offers more than the minimal shape.
# =============================================================================


_RECIPE_MD_TEMPLATE = """\
---
id: {recipe_id}
version: 0.1.0
name: "{display_name}"
description: "TODO: write a self-contained description used by agents to pick this recipe. At least 50 characters."
use_when: "TODO: explain when an agent should pick this recipe over alternatives."
produces: evidence
author: "{author}"
license: Apache-2.0
# Optional fields — uncomment and populate as needed.
# attests:
#   - {{ control: AC-2, framework: nist-800-53-r5 }}
# params:
#   target:
#     type: string
#     description: "Example parameter the calling agent supplies."
# requires:
#   cli:
#     - {{ name: example-binary, probe: "example-binary --version" }}
#   env:
#     - EXAMPLE_TOKEN
# scripts:
#   example_tool:
#     path: scripts/example.py
#     description: "What this tool does, surfaced to the agent."
#     params:
#       input:
#         type: string
#         description: "Tool-specific input."
---

# {display_name}

This is the playbook the calling agent reads. Describe the procedure here in
plain English — the agent follows these instructions and calls pretorin tools
(via MCP or `pretorin agent run`) to produce the evidence or narrative.

The body is not executed by pretorin. It is read by whichever agent invokes
the recipe. Be explicit about expected inputs, ordering, and outputs.
"""


_SCRIPT_TEMPLATE = """\
\"\"\"{tool_name} script for the {recipe_id} recipe.\"\"\"

from __future__ import annotations

from typing import Any


async def run(ctx: Any, **params: Any) -> dict[str, Any]:
    \"\"\"Tool entry point invoked by the recipe runtime.

    Per RFC 0001 §Contract versioning (frozen in v1): each script in a recipe
    exposes one ``async run(ctx, **params) -> dict`` callable. The dict return
    is whatever the calling agent needs.

    Args:
        ctx: Recipe execution context object (system_id, framework_id,
            authenticated API client, structured logger, recipe id/version).
        **params: Tool-specific inputs, validated against the manifest's
            ScriptDecl.params schema.
    \"\"\"
    # TODO: implement the tool.
    return {{"status": "todo", "params": params}}
"""


_README_TEMPLATE = """\
# {display_name}

Recipe id: `{recipe_id}`
Author: {author}
License: Apache-2.0

## What this recipe does

TODO: describe the procedure for human readers.

## How to invoke

```
pretorin recipe run {recipe_id}
```

Or, via MCP from your local agent (Claude Code, Codex CLI, etc.), call
``pretorin_start_recipe(recipe_id="{recipe_id}", recipe_version="0.1.0", params={{...}})``.

## Tests

Add fixtures and unit tests under ``tests/`` following the patterns in the
pretorin test suite.
"""


# =============================================================================
# `pretorin recipe list`
# =============================================================================


@app.command("list")
def recipe_list(
    tier: str | None = typer.Option(
        None,
        "--tier",
        help="Filter to one tier (official, partner, community).",
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Filter to one loader source (builtin, user, project, explicit).",
    ),
) -> None:
    """List all loaded recipes with id, name, tier, author, and source path.

    Recipes whose id is shadowed by another loader path are marked with ``*``.
    Use ``pretorin recipe show <id> --sources`` to see the shadowing detail.
    """
    registry = RecipeRegistry()
    entries = registry.entries()

    if tier:
        entries = [e for e in entries if e.active.manifest.tier == tier]
    if source:
        entries = [e for e in entries if e.active.source == source]

    if is_json_mode():
        print_json(
            [
                {
                    "id": e.active.manifest.id,
                    "name": e.active.manifest.name,
                    "tier": e.active.manifest.tier,
                    "author": e.active.manifest.author,
                    "version": e.active.manifest.version,
                    "produces": e.active.manifest.produces,
                    "source": e.active.source,
                    "path": str(e.active.path),
                    "shadowed": [{"source": s.source, "path": str(s.path)} for s in e.shadowed],
                }
                for e in entries
            ]
        )
        return

    if not entries:
        rprint("[dim]No recipes found.[/dim]")
        return

    table = Table(title="Recipes")
    # no_wrap=True on ID + Source so the user's lookup key never gets truncated
    # by Rich's auto-column-shrink when the terminal is narrow (e.g., CI / tests).
    table.add_column("ID", style="bold", no_wrap=True)
    table.add_column("Name")
    table.add_column("Tier", no_wrap=True)
    table.add_column("Author")
    table.add_column("Version", no_wrap=True)
    table.add_column("Source", no_wrap=True)

    has_shadow = False
    for entry in entries:
        rid = entry.active.manifest.id
        marker = "*" if entry.shadowed else ""
        if entry.shadowed:
            has_shadow = True
        table.add_row(
            f"{rid}{marker}",
            entry.active.manifest.name,
            entry.active.manifest.tier,
            entry.active.manifest.author,
            entry.active.manifest.version,
            entry.active.source,
        )

    console.print(table)
    if has_shadow:
        rprint(
            "[dim]* indicates the recipe id is shadowed (active version overrides "
            "another path's copy). Run [bold]pretorin recipe show <id> "
            "--sources[/bold] to see all locations.[/dim]"
        )


# =============================================================================
# `pretorin recipe show <id>`
# =============================================================================


@app.command("show")
def recipe_show(
    recipe_id: str = typer.Argument(..., help="Recipe id to display."),
    sources: bool = typer.Option(
        False,
        "--sources",
        help="List every loader path the id appears at, marking the active one.",
    ),
) -> None:
    """Display a recipe's manifest, body, and (optionally) all source paths."""
    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    if entry is None:
        rprint(f"[red]No recipe found with id {recipe_id!r}.[/red]")
        raise typer.Exit(1)

    if is_json_mode():
        print_json(
            {
                "id": entry.active.manifest.id,
                "manifest": entry.active.manifest.model_dump(),
                "body": entry.active.body,
                "active_source": entry.active.source,
                "active_path": str(entry.active.path),
                "shadowed": [{"source": s.source, "path": str(s.path)} for s in entry.shadowed],
            }
        )
        return

    m = entry.active.manifest
    rprint(f"[bold]{m.id}[/bold] — {m.name}")
    rprint(f"  Tier:        {m.tier}")
    rprint(f"  Version:     {m.version}")
    rprint(f"  Author:      {m.author}")
    rprint(f"  License:     {m.license}")
    rprint(f"  Produces:    {m.produces}")
    rprint(f"  Description: {m.description}")
    rprint(f"  Use when:    {m.use_when}")
    if m.scripts:
        rprint(f"  Scripts:     {', '.join(m.scripts.keys())}")
    if m.attests:
        rprint(f"  Attests:     {m.attests}")

    if sources:
        rprint("\n[bold]Sources:[/bold]")
        rprint(f"  [green]ACTIVE[/green]   {entry.active.source}: {entry.active.path}")
        for s in entry.shadowed:
            rprint(f"  [dim]shadowed[/dim] {s.source}: {s.path}")

    rprint("\n[bold]Body:[/bold]")
    rprint(entry.active.body)


# =============================================================================
# `pretorin recipe new <id>`
# =============================================================================


@app.command("new")
def recipe_new(
    recipe_id: str = typer.Argument(..., help="Recipe id (lowercase-kebab-case)."),
    location: str = typer.Option(
        "user",
        "--location",
        help="Where to create the recipe: user, project, or builtin.",
    ),
    author: str = typer.Option(
        "",
        "--author",
        help="Author name to populate in recipe.md (defaults to current user).",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Display name for the recipe (defaults to a title-cased id).",
    ),
) -> None:
    """Scaffold a new recipe directory with a templated recipe.md, script stub, README.

    Default location is the user folder (``~/.pretorin/recipes/``) so contributors
    can ship a first recipe without forking pretorin. Use ``--location project``
    for team-shared recipes checked into a compliance repo, or ``--location
    builtin`` for first-party recipes inside ``src/pretorin/recipes/``.
    """
    # Validate id format up-front by feeding it through the manifest schema.
    try:
        RecipeManifest.model_validate(
            {
                "id": recipe_id,
                "version": "0.1.0",
                "name": "validation-only",
                "description": "validation-only ten characters at least",
                "use_when": "validation-only",
                "produces": "evidence",
                "author": "validation-only",
            }
        )
    except Exception as exc:
        rprint(f"[red]Invalid recipe id {recipe_id!r}: {exc}[/red]")
        raise typer.Exit(1) from exc

    target_root = _resolve_new_location(location)
    if target_root is None:
        rprint(f"[red]Unknown --location {location!r}. Use one of: user, project, builtin.[/red]")
        raise typer.Exit(1)

    target_dir = target_root / recipe_id
    if target_dir.exists():
        rprint(f"[red]Recipe directory already exists: {target_dir}[/red]")
        raise typer.Exit(1)

    target_dir.mkdir(parents=True)
    (target_dir / "scripts").mkdir()

    display_name = name if name else recipe_id.replace("-", " ").title()
    author_name = author or _default_author()

    (target_dir / "recipe.md").write_text(
        _RECIPE_MD_TEMPLATE.format(
            recipe_id=recipe_id,
            display_name=display_name,
            author=author_name,
        )
    )
    (target_dir / "scripts" / "example.py").write_text(
        _SCRIPT_TEMPLATE.format(tool_name="example_tool", recipe_id=recipe_id)
    )
    (target_dir / "README.md").write_text(
        _README_TEMPLATE.format(
            recipe_id=recipe_id,
            display_name=display_name,
            author=author_name,
        )
    )
    (target_dir / "tests").mkdir()
    (target_dir / "tests" / "__init__.py").write_text("")

    rprint(f"[green]Recipe scaffolded at:[/green] {target_dir}")
    rprint("Next steps:")
    rprint(f"  1. Edit {target_dir / 'recipe.md'} (description + use_when matter most)")
    rprint(f"  2. Run [bold]pretorin recipe validate {recipe_id}[/bold] to check it")
    rprint(f"  3. Implement [bold]{target_dir / 'scripts' / 'example.py'}[/bold] (or remove it)")


# =============================================================================
# `pretorin recipe validate <id>`
# =============================================================================


@app.command("validate")
def recipe_validate(
    recipe_id: str = typer.Argument(..., help="Recipe id to validate."),
    explicit_path: Path | None = typer.Option(
        None,
        "--path",
        help="Validate a recipe directory by absolute path instead of by id.",
    ),
) -> None:
    """Validate a recipe's manifest, scripts, and description quality.

    Three checks beyond the manifest schema:
    - Each script's ``path`` resolves to a file that exists.
    - Each script file has a top-level ``async def run`` callable.
    - ``description`` is at least 50 characters and ``use_when`` at least 30
      characters (the bar for a description an LLM can pick from).
    """
    issues: list[str] = []

    if explicit_path is not None:
        try:
            loaded = load_explicit_path(explicit_path)
        except RecipeManifestError as exc:
            rprint(f"[red]Manifest invalid: {exc}[/red]")
            raise typer.Exit(1) from exc
    else:
        registry = RecipeRegistry()
        entry = registry.get(recipe_id)
        if entry is None:
            rprint(f"[red]No recipe found with id {recipe_id!r}.[/red]")
            raise typer.Exit(1)
        loaded = entry.active

    m = loaded.manifest
    recipe_dir = loaded.path.parent

    # Description-quality checks (the contract is the description; sharp it
    # before code is the WS3 assignment but recipes elsewhere need the same bar).
    if len(m.description) < 50:
        issues.append(
            f"description is too short ({len(m.description)} chars, need ≥ 50). "
            "Consider expanding to explain what the recipe does and when to pick it."
        )
    if len(m.use_when) < 30:
        issues.append(
            f"use_when is too short ({len(m.use_when)} chars, need ≥ 30). "
            "Make it explicit: 'when the agent has X and needs Y'."
        )

    # Per-script existence + signature check.
    for tool_name, decl in m.scripts.items():
        script_path = (recipe_dir / decl.path).resolve()
        if not script_path.is_file():
            issues.append(f"script {tool_name!r} declares path {decl.path!r}, but {script_path} does not exist.")
            continue
        try:
            script_text = script_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(f"script {tool_name!r} at {script_path} could not be read: {exc}")
            continue
        if "async def run" not in script_text:
            issues.append(f"script {tool_name!r} at {script_path} must define `async def run(ctx, **params) -> dict`.")

    if is_json_mode():
        print_json({"id": m.id, "valid": not issues, "issues": issues})
        return

    if not issues:
        rprint(f"[green]{m.id} validates cleanly.[/green]")
        return

    rprint(f"[red]{m.id} has {len(issues)} issue(s):[/red]")
    for i, msg in enumerate(issues, 1):
        rprint(f"  {i}. {msg}")
    raise typer.Exit(1)


# =============================================================================
# `pretorin recipe run <id>`
# =============================================================================


@app.command("run")
def recipe_run(
    recipe_id: str = typer.Argument(..., help="Recipe id to run."),
    script: str | None = typer.Option(
        None,
        "--script",
        "-s",
        help="Script name from the recipe's scripts: map. Defaults to the only script if exactly one is declared.",
    ),
    params: list[str] = typer.Option(
        None,
        "--param",
        "-p",
        help="Param key=value pairs (repeatable). Values are parsed as JSON; falls back to string on parse failure.",
    ),
    explicit_path: Path | None = typer.Option(
        None,
        "--path",
        help="Run a recipe directory by absolute path instead of by registry id.",
    ),
    system: str | None = typer.Option(
        None,
        "--system",
        help=(
            "System name or id. Required if the recipe needs a system; resolved against active CLI context if omitted."
        ),
    ),
    framework: str | None = typer.Option(
        None,
        "--framework",
        help="Framework id (e.g., nist-800-53-r5).",
    ),
    no_context: bool = typer.Option(
        False,
        "--no-context",
        help=(
            "Skip opening a recipe execution context. Use for pure "
            "transformation recipes that don't write to the platform."
        ),
    ),
) -> None:
    """Run a recipe's script locally for testing.

    Loads the recipe from the registry (or ``--path``), resolves its script,
    opens a recipe execution context, calls the script, prints the result,
    closes the context.

    This is a **local testing** path. The context lives in the CLI process, so
    writes that flow through ``ctx.api_client`` directly need explicit
    ``audit_metadata`` (see ``docs/src/recipes/writer-tools.md``). The MCP
    boundary stamps it automatically; this command does not.
    """
    asyncio.run(
        _recipe_run(
            recipe_id=recipe_id,
            script=script,
            param_specs=list(params or []),
            explicit_path=explicit_path,
            system=system,
            framework=framework,
            no_context=no_context,
        )
    )


async def _recipe_run(
    *,
    recipe_id: str,
    script: str | None,
    param_specs: list[str],
    explicit_path: Path | None,
    system: str | None,
    framework: str | None,
    no_context: bool,
) -> None:
    if explicit_path is not None:
        try:
            loaded = load_explicit_path(explicit_path)
        except RecipeManifestError as exc:
            rprint(f"[red]Recipe failed to load from {explicit_path}: {exc}[/red]")
            raise typer.Exit(1) from exc
    else:
        registry = RecipeRegistry()
        entry = registry.get(recipe_id)
        if entry is None:
            rprint(f"[red]No recipe found with id {recipe_id!r}.[/red]")
            raise typer.Exit(1)
        loaded = entry.active

    manifest = loaded.manifest
    script_name = _resolve_script_name(manifest, script)
    if script_name is None:
        scripts = sorted(manifest.scripts.keys())
        rprint(
            f"[red]Recipe {manifest.id!r} declares {len(scripts)} script(s); "
            f"specify one with --script. Available: {scripts}[/red]"
        )
        raise typer.Exit(1)

    parsed_params = _parse_param_specs(param_specs)

    # Resolve scope. Avoid hitting the network unless we actually need it.
    from pretorin.client.api import PretorianClient

    async with PretorianClient() as client:
        system_id, framework_id = await _resolve_run_scope(client, system, framework)

        context_id: str | None = None
        if not no_context:
            try:
                ctx_record = get_default_store().start_recipe(
                    recipe_id=manifest.id,
                    recipe_version=manifest.version,
                    params=parsed_params,
                )
                context_id = ctx_record.context_id
            except RecipeContextError as exc:
                rprint(f"[red]Could not open recipe context: {exc}[/red]")
                raise typer.Exit(1) from exc

        script_ctx = RecipeScriptContext(
            system_id=system_id,
            framework_id=framework_id,
            api_client=client,
            logger=logging.getLogger(f"pretorin.recipe.{manifest.id}"),
            recipe_id=manifest.id,
            recipe_version=manifest.version,
            recipe_context_id=context_id,
        )

        try:
            result = await run_script(
                recipe=loaded,
                script_name=script_name,
                ctx=script_ctx,
                params=parsed_params,
            )
        finally:
            if context_id is not None:
                try:
                    get_default_store().end_recipe(context_id, status="pass")
                except RecipeContextError:
                    pass

    if is_json_mode():
        print_json(
            {
                "recipe_id": manifest.id,
                "recipe_version": manifest.version,
                "script": script_name,
                "context_id": context_id,
                "result": result,
            }
        )
        return

    rprint(f"[bold]{manifest.id}[/bold] / [bold]{script_name}[/bold]")
    if context_id:
        rprint(f"[dim]context_id: {context_id}[/dim]")
    rprint("[bold]Result:[/bold]")
    rprint(json.dumps(result, indent=2, default=str))


def _resolve_script_name(manifest: RecipeManifest, script: str | None) -> str | None:
    """Pick which script to run. Returns None when ambiguous and not specified."""
    if script is not None:
        if script not in manifest.scripts:
            return None
        return script
    if len(manifest.scripts) == 1:
        return next(iter(manifest.scripts))
    return None


def _parse_param_specs(specs: list[str]) -> dict[str, Any]:
    """Parse ``--param key=value`` repetitions into a dict.

    Values are JSON-parsed first (so ``--param limit=20`` lands as int 20 and
    ``--param items='[1,2]'`` lands as a list). On JSON parse failure, the
    value is kept as the raw string so simple ``--param target=local`` works
    without quoting.
    """
    parsed: dict[str, Any] = {}
    for spec in specs:
        if "=" not in spec:
            raise typer.BadParameter(f"--param must be key=value; got {spec!r}")
        key, raw = spec.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"--param has empty key: {spec!r}")
        try:
            parsed[key] = json.loads(raw)
        except json.JSONDecodeError:
            parsed[key] = raw
    return parsed


async def _resolve_run_scope(
    client: Any,
    system: str | None,
    framework: str | None,
) -> tuple[str | None, str | None]:
    """Resolve system + framework to ids, allowing both to be None.

    Recipes that don't need a system (pure data-transformation recipes like
    code-evidence-capture's redact_secrets) can be run with no scope at all.
    The runner won't reach out to the platform unless the script does.
    """
    system_id: str | None = None
    if system is not None:
        from pretorin.workflows.compliance_updates import resolve_system

        system_id, _ = await resolve_system(client, system)
    return system_id, framework


# =============================================================================
# Helpers
# =============================================================================


def _resolve_new_location(location: str) -> Path | None:
    """Map ``--location`` to a parent directory where the new recipe lands.

    Goes through the loader's path resolvers (``_user_recipes_root`` and
    ``_builtin_recipes_root``) rather than building paths directly, so the
    scaffolder and the registry always agree on where recipes live. Tests
    that monkeypatch the loader's resolvers automatically affect the
    scaffolder too — no second monkeypatch needed.
    """
    from pretorin.recipes import loader as loader_module

    if location == "user":
        root = loader_module._user_recipes_root()
        root.mkdir(parents=True, exist_ok=True)
        return root
    if location == "project":
        # New project recipes always go under <cwd>/.pretorin/recipes/ even
        # if the registry walks up the tree from cwd to find the same dir.
        root = Path.cwd() / ".pretorin" / "recipes"
        root.mkdir(parents=True, exist_ok=True)
        return root
    if location == "builtin":
        root = loader_module._builtin_recipes_root()
        root.mkdir(parents=True, exist_ok=True)
        return root
    return None


def _default_author() -> str:
    """Best-effort author attribution from local git or env."""
    import os
    import subprocess

    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return os.environ.get("USER") or "unknown"


__all__ = ["app"]
