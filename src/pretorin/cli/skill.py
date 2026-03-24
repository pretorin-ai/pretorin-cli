"""Skill installation CLI commands for Pretorin."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

app = typer.Typer()
console = Console()

SKILL_NAME = "pretorin"

# Registry of known agents and their global skills directories.
# Path patterns use {home} (resolved at runtime) and {skill} (the skill name).
# Adding a new agent is a one-line addition here.
KNOWN_AGENTS: dict[str, str] = {
    "claude": "{home}/.claude/skills/{skill}",
    "codex": "{home}/.codex/skills/{skill}",
}


def _skill_source() -> Path:
    """Return the path to the bundled skill data.

    In wheel installs, hatch force-include places skill_data/ inside the
    package.  In editable/dev installs that directory doesn't exist, so
    we fall back to the repo-root pretorin-skill/ directory.
    """
    # Wheel install: skill_data/ is inside the package
    pkg_path = Path(__file__).resolve().parent.parent / "skill_data"
    if (pkg_path / "SKILL.md").exists():
        return pkg_path
    # Editable / dev install: use the repo-root canonical copy
    repo_path = Path(__file__).resolve().parent.parent.parent.parent / "pretorin-skill"
    if (repo_path / "SKILL.md").exists():
        return repo_path
    return pkg_path  # fall through — _install_to will surface a clear error


def _resolve_target(agent: str) -> Path:
    """Resolve the install target directory for a known agent."""
    pattern = KNOWN_AGENTS[agent]
    return Path(pattern.format(home=Path.home(), skill=SKILL_NAME))


def _is_installed_at(target: Path) -> bool:
    """Check whether the skill is installed at a given path."""
    return (target / "SKILL.md").exists()


def _install_to(target: Path, *, force: bool = False) -> tuple[bool, str]:
    """Install the skill to a target directory. Returns (success, message)."""
    source = _skill_source()
    if not (source / "SKILL.md").exists():
        return False, "Bundled skill data not found — reinstall pretorin."

    if target.exists() and not force:
        return False, f"Already installed at {target}. Use --force to overwrite."

    if target.exists():
        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)

    return True, str(target)


def _uninstall_from(target: Path) -> tuple[bool, str]:
    """Uninstall the skill from a target directory. Returns (success, message)."""
    if not target.exists():
        return False, "Not installed."

    shutil.rmtree(target)
    return True, str(target)


def _resolve_targets(
    agents: list[str] | None,
    path: Path | None,
) -> list[tuple[str, Path]]:
    """Build a list of (label, target_path) pairs from CLI arguments."""
    if path is not None:
        # Explicit path — single target, label is the directory name
        resolved = path / SKILL_NAME if path.name != SKILL_NAME else path
        return [(str(resolved.parent.name), resolved)]

    if agents:
        unknown = [a for a in agents if a not in KNOWN_AGENTS]
        if unknown:
            known_list = ", ".join(sorted(KNOWN_AGENTS))
            rprint(f"[#FF9010]![/#FF9010] Unknown agent(s): {', '.join(unknown)}. Known agents: {known_list}")
            rprint("[dim]Use --path to install to a custom directory.[/dim]")
            raise typer.Exit(1)
        return [(a, _resolve_target(a)) for a in agents]

    # Default: all known agents
    return [(a, _resolve_target(a)) for a in KNOWN_AGENTS]


@app.command()
def install(
    agents: list[str] | None = typer.Option(
        None,
        "--agent",
        "-a",
        help=f"Target agent(s): {', '.join(KNOWN_AGENTS)}. Omit to install for all.",
    ),
    path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Custom skills directory (for agents not in the built-in registry).",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing installation"),
) -> None:
    """Install the Pretorin skill for AI coding agents.

    Copies the skill (SKILL.md + references) into each agent's global skills
    directory so it's available in every project.

    Use --agent to target specific agents, or --path for a custom directory.
    """
    targets = _resolve_targets(agents, path)

    if is_json_mode():
        results = {}
        for label, target in targets:
            ok, msg = _install_to(target, force=force)
            results[label] = {"installed": ok, "message": msg}
        print_json(results)
        return

    for label, target in targets:
        ok, msg = _install_to(target, force=force)
        display = label.capitalize()
        if ok:
            rprint(f"  [#95D7E0]✓[/#95D7E0] {display}: installed to [bold]{msg}[/bold]")
        else:
            rprint(f"  [#FF9010]![/#FF9010] {display}: {msg}")

    rprint()
    rprint("[dim]The skill teaches your agent how to use Pretorin MCP tools for compliance workflows.[/dim]")


@app.command()
def uninstall(
    agents: list[str] | None = typer.Option(
        None,
        "--agent",
        "-a",
        help=f"Target agent(s): {', '.join(KNOWN_AGENTS)}. Omit to uninstall from all.",
    ),
    path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Custom skills directory to uninstall from.",
    ),
) -> None:
    """Remove the Pretorin skill from AI coding agents."""
    targets = _resolve_targets(agents, path)

    if is_json_mode():
        results = {}
        for label, target in targets:
            ok, msg = _uninstall_from(target)
            results[label] = {"uninstalled": ok, "message": msg}
        print_json(results)
        return

    for label, target in targets:
        ok, msg = _uninstall_from(target)
        display = label.capitalize()
        if ok:
            rprint(f"  [#95D7E0]✓[/#95D7E0] {display}: removed from [bold]{msg}[/bold]")
        else:
            rprint(f"  [dim]  {display}: {msg}[/dim]")


@app.command()
def status() -> None:
    """Show which agents have the Pretorin skill installed."""
    if is_json_mode():
        results = {}
        for agent, _pattern in KNOWN_AGENTS.items():
            target = _resolve_target(agent)
            results[agent] = {
                "installed": _is_installed_at(target),
                "path": str(target),
            }
        print_json(results)
        return

    table = Table(show_header=True, header_style="bold #FF9010")
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Path")

    for agent in KNOWN_AGENTS:
        target = _resolve_target(agent)
        installed = _is_installed_at(target)
        status_text = "[#95D7E0]installed[/#95D7E0]" if installed else "[dim]not installed[/dim]"
        table.add_row(agent.capitalize(), status_text, str(target))

    console.print(table)


@app.command("list-agents")
def list_agents() -> None:
    """List all known agents and their skill directories."""
    if is_json_mode():
        print_json({agent: str(_resolve_target(agent)) for agent in KNOWN_AGENTS})
        return

    table = Table(show_header=True, header_style="bold #FF9010")
    table.add_column("Agent")
    table.add_column("Skills Directory")

    for agent in KNOWN_AGENTS:
        table.add_row(agent, str(_resolve_target(agent)))

    console.print(table)
    rprint("\n[dim]Use --path to install to a custom directory for unlisted agents.[/dim]")
