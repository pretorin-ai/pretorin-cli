"""``pretorin recipe`` CLI commands.

Phase A2 of the recipe-implementation design: the user-facing surface that
unblocks the contributor workflow. ``pretorin recipe new`` scaffolds a recipe,
``pretorin recipe validate`` checks it, ``pretorin recipe list / show`` are the
read-side surface over the registry. ``pretorin recipe run`` and the
recipe-execution-context wiring land in Phase B.

Per the design's "Extensibility — Community Contribution Surface" section,
``pretorin recipe new`` defaults to ``--location user`` so a contributor can
ship their first recipe without a fork.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.recipes.errors import RecipeManifestError
from pretorin.recipes.loader import load_explicit_path
from pretorin.recipes.manifest import RecipeManifest
from pretorin.recipes.registry import RecipeRegistry

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
