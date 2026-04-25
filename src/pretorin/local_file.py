"""Shared utilities for local markdown files with YAML frontmatter.

The narrative, notes, and evidence writer/sync modules all need to
sanitize paths, generate slugs, parse frontmatter, and rewrite
frontmatter in-place.  This module is the single source of truth for
those operations — the per-domain modules import from here.
"""

from __future__ import annotations

import re
from pathlib import Path


def safe_path_component(text: str) -> str:
    """Sanitize a string for use as a path component (no traversal)."""
    cleaned = text.replace("/", "").replace("\\", "").replace("\0", "")
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = cleaned.strip(". ")
    if not cleaned:
        raise ValueError(f"Invalid path component: {text!r}")
    return cleaned


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].rstrip("-")


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file.

    Returns:
        Tuple of (frontmatter dict, body text).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

    fm: dict[str, str] = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()

    return fm, body


def update_file_frontmatter(path: Path, new_frontmatter: str) -> None:
    """Rewrite a file's YAML frontmatter in-place, preserving the body."""
    if not path.exists():
        return

    content = path.read_text()

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            path.write_text(f"{new_frontmatter}\n{body}")
