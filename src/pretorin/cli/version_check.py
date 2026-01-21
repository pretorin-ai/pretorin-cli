"""Version check utility for Pretorin CLI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pretorin import __version__

# Cache file for version check (avoid hitting PyPI every time)
CACHE_DIR = Path.home() / ".pretorin"
VERSION_CACHE_FILE = CACHE_DIR / ".version_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours

PYPI_URL = "https://pypi.org/pypi/pretorin/json"


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a tuple for comparison."""
    try:
        # Handle versions like "0.1.0", "1.2.3", "2.0.0a1"
        # Strip any suffix like "a1", "b2", "rc1"
        clean = version.split("a")[0].split("b")[0].split("rc")[0]
        return tuple(int(x) for x in clean.split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _load_cache() -> dict[str, Any]:
    """Load the version cache file."""
    if VERSION_CACHE_FILE.exists():
        try:
            with open(VERSION_CACHE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(data: dict[str, Any]) -> None:
    """Save the version cache file."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(VERSION_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass  # Fail silently - version check is non-critical


def _fetch_latest_version() -> str | None:
    """Fetch the latest version from PyPI."""
    try:
        import urllib.request

        req = urllib.request.Request(
            PYPI_URL,
            headers={"Accept": "application/json", "User-Agent": f"pretorin-cli/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            return data.get("info", {}).get("version")
    except Exception:
        return None


def check_for_updates() -> str | None:
    """Check if a newer version is available.

    Returns the latest version string if an update is available,
    or None if the CLI is up to date (or if the check fails).

    Results are cached for 24 hours to avoid excessive API calls.
    """
    # Check cache first
    cache = _load_cache()
    cached_time = cache.get("checked_at", 0)
    cached_version = cache.get("latest_version")

    now = time.time()

    # Use cached result if still fresh
    if cached_version and (now - cached_time) < CACHE_TTL_SECONDS:
        latest = cached_version
    else:
        # Fetch from PyPI
        latest = _fetch_latest_version()
        if latest:
            _save_cache({"latest_version": latest, "checked_at": now})

    if not latest:
        return None

    # Compare versions
    current_tuple = _parse_version(__version__)
    latest_tuple = _parse_version(latest)

    if latest_tuple > current_tuple:
        return latest

    return None


def get_update_message() -> str | None:
    """Get a formatted update message if an update is available."""
    latest = check_for_updates()
    if latest:
        return (
            f"[#FF9010]→[/#FF9010] A newer version of Pretorin CLI is available "
            f"([#EAB536]{latest}[/#EAB536])\n"
            f"  [dim]Run:[/dim] [bold]pip install --upgrade pretorin[/bold]"
        )
    return None
