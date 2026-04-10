"""Version check utility for Pretorin CLI."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pretorin import __version__
from pretorin.client.config import Config

# Cache file for version check (avoid hitting PyPI every time)
CACHE_DIR = Path.home() / ".pretorin"
VERSION_CACHE_FILE = CACHE_DIR / ".version_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours
FAILURE_CACHE_TTL_SECONDS = 3600  # 1 hour
REQUEST_TIMEOUT_SECONDS = 1.0

PYPI_URL = "https://pypi.org/pypi/pretorin/json"
UPGRADE_COMMAND = "pip install --upgrade pretorin"


@dataclass(frozen=True)
class VersionCheckResult:
    """Outcome of a passive version check."""

    latest_version: str | None
    update_available: bool
    checked: bool


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
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode())
            return data.get("info", {}).get("version")
    except Exception:
        return None


def _cache_fresh(cache: dict[str, Any], now: float) -> bool:
    """Check whether cached version-check data is still usable."""
    next_check_at = cache.get("next_check_at")
    if isinstance(next_check_at, (int, float)):
        return now < float(next_check_at)

    cache = _load_cache()
    cached_time = cache.get("checked_at", 0)
    cached_version = cache.get("latest_version")
    last_result = cache.get("last_result", "success" if cached_version else "failure")
    ttl = CACHE_TTL_SECONDS if last_result == "success" else FAILURE_CACHE_TTL_SECONDS
    return (now - float(cached_time)) < ttl


def update_notifications_enabled() -> bool:
    """Return whether passive update notifications should be shown."""
    return not Config().disable_update_check


def check_for_updates(*, force: bool = False) -> VersionCheckResult:
    """Check whether a newer version is available.

    Passive checks fail closed: network/cache issues return a non-fatal
    result with ``checked=False`` and no update notification.
    """
    cache = _load_cache()

    now = time.time()

    # Use cached result if still fresh
    if not force and _cache_fresh(cache, now):
        if cache.get("last_result") == "failure":
            return VersionCheckResult(latest_version=None, update_available=False, checked=False)
        latest = cache.get("latest_version")
    else:
        # Fetch from PyPI
        latest = _fetch_latest_version()
        if latest:
            _save_cache(
                {
                    "latest_version": latest,
                    "checked_at": now,
                    "next_check_at": now + CACHE_TTL_SECONDS,
                    "last_result": "success",
                }
            )
        else:
            _save_cache(
                {
                    "latest_version": None,
                    "checked_at": now,
                    "next_check_at": now + FAILURE_CACHE_TTL_SECONDS,
                    "last_result": "failure",
                }
            )
            return VersionCheckResult(latest_version=None, update_available=False, checked=False)

    if not latest:
        return VersionCheckResult(latest_version=None, update_available=False, checked=False)

    # Compare versions
    current_tuple = _parse_version(__version__)
    latest_tuple = _parse_version(latest)

    return VersionCheckResult(
        latest_version=latest,
        update_available=latest_tuple > current_tuple,
        checked=True,
    )


def get_update_status(*, force: bool = False) -> dict[str, Any]:
    """Return structured CLI update status for CLI and MCP surfaces."""
    notifications_enabled = update_notifications_enabled()
    status: dict[str, Any] = {
        "current_version": __version__,
        "latest_version": None,
        "update_available": False,
        "checked": False,
        "notifications_enabled": notifications_enabled,
        "upgrade_command": UPGRADE_COMMAND,
        "message": "Passive update notifications are disabled.",
        "prompt": None,
    }

    if not notifications_enabled:
        return status

    result = check_for_updates(force=force)
    status["latest_version"] = result.latest_version
    status["update_available"] = result.update_available
    status["checked"] = result.checked

    if result.update_available and result.latest_version:
        prompt = (
            f"A newer version of Pretorin CLI is available ({result.latest_version}). "
            f"Run: {UPGRADE_COMMAND}"
        )
        status["message"] = prompt
        status["prompt"] = prompt
    elif result.checked:
        status["message"] = "Pretorin CLI is up to date."
    else:
        status["message"] = "Unable to check for updates right now."

    return status


def get_update_message() -> str | None:
    """Get a formatted update message if an update is available."""
    status = get_update_status()
    latest_version = status.get("latest_version")
    if status.get("update_available") and latest_version:
        return (
            f"[#FF9010]→[/#FF9010] A newer version of Pretorin CLI is available "
            f"([#EAB536]{latest_version}[/#EAB536])\n"
            f"  [dim]Run:[/dim] [bold]{UPGRADE_COMMAND}[/bold]"
        )
    return None
