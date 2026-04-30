"""Workflow loader + registry. Single-file because workflows are simple.

Recipes have four loader paths and shadowing rules; workflows are first-party
only in v1 (built-in path), so the loader is one function over one directory.
If community workflows ship in v1.5, this expands to mirror
``pretorin.recipes.loader``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from pretorin.workflows_lib.manifest import WorkflowManifest

logger = logging.getLogger(__name__)


@dataclass
class LoadedWorkflow:
    """One workflow.md after parsing + validation."""

    manifest: WorkflowManifest
    body: str
    path: Path


def _builtin_workflows_root() -> Path:
    """Built-in workflow playbooks under the package."""
    return Path(__file__).resolve().parent / "_workflows"


def _parse_frontmatter(content: str, path: Path) -> tuple[dict[str, object], str]:
    """Same shape as the recipes loader; kept local so we don't import privately."""
    if not content.startswith("---"):
        raise ValueError(f"workflow.md at {path} must start with YAML frontmatter")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"workflow.md at {path} has unterminated frontmatter")
    fm_text = parts[1].strip()
    body = parts[2].lstrip("\n")
    fm_loaded = yaml.safe_load(fm_text)
    if fm_loaded is None:
        return {}, body
    if not isinstance(fm_loaded, dict):
        raise ValueError(f"workflow.md at {path} frontmatter must be a YAML mapping")
    return fm_loaded, body


def _load_one(path: Path) -> LoadedWorkflow | None:
    """Parse + validate one workflow. Returns None on failure with a debug log."""
    try:
        content = path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(content, path)
        manifest = WorkflowManifest.model_validate(frontmatter)
    except Exception as exc:
        logger.warning("Workflow at %s failed to load: %s", path, exc)
        return None
    return LoadedWorkflow(manifest=manifest, body=body, path=path.resolve())


def load_all() -> list[LoadedWorkflow]:
    """Walk the built-in workflows root and return every valid workflow."""
    root = _builtin_workflows_root()
    if not root.is_dir():
        return []
    out: list[LoadedWorkflow] = []
    for workflow_md in sorted(root.glob("*/workflow.md")):
        loaded = _load_one(workflow_md)
        if loaded is not None:
            out.append(loaded)
    return out


def get_workflow(workflow_id: str) -> LoadedWorkflow | None:
    """Look up one workflow by id. Returns None when not found."""
    for w in load_all():
        if w.manifest.id == workflow_id:
            return w
    return None


__all__ = [
    "LoadedWorkflow",
    "get_workflow",
    "load_all",
]
