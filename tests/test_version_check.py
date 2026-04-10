"""Tests for passive CLI update checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from pretorin.cli import version_check
from pretorin.client import config as config_module


@pytest.fixture
def isolated_update_paths(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect version-check cache and config to a temp directory."""
    config_dir = tmp_path / ".pretorin"
    config_file = config_dir / "config.json"
    cache_file = config_dir / ".version_cache.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    monkeypatch.setattr(version_check, "CACHE_DIR", config_dir)
    monkeypatch.setattr(version_check, "VERSION_CACHE_FILE", cache_file)
    return cache_file


def test_get_update_message_respects_env_opt_out(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    monkeypatch.setenv(config_module.ENV_DISABLE_UPDATE_CHECK, "1")
    monkeypatch.setattr(
        version_check,
        "check_for_updates",
        lambda force=False: version_check.VersionCheckResult(
            latest_version="9.9.9",
            update_available=True,
            checked=True,
        ),
    )

    assert version_check.get_update_message() is None


def test_get_update_message_respects_config_opt_out(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    cfg = config_module.Config()
    cfg.set("disable_update_check", "true")
    monkeypatch.setattr(
        version_check,
        "check_for_updates",
        lambda force=False: version_check.VersionCheckResult(
            latest_version="9.9.9",
            update_available=True,
            checked=True,
        ),
    )

    assert version_check.get_update_message() is None


def test_failed_fetch_is_cached(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    calls = {"count": 0}

    def fail_fetch() -> None:
        calls["count"] += 1
        return None

    monkeypatch.setattr(version_check, "_fetch_latest_version", fail_fetch)

    first = version_check.check_for_updates()
    second = version_check.check_for_updates()

    assert first.checked is False
    assert second.checked is False
    assert calls["count"] == 1


def test_get_update_message_uses_cached_success(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    monkeypatch.setattr(version_check, "_fetch_latest_version", lambda: "9.9.9")

    message = version_check.get_update_message()

    assert message is not None
    assert "9.9.9" in message


def test_get_update_status_includes_prompt_when_update_available(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    monkeypatch.setattr(version_check, "_fetch_latest_version", lambda: "9.9.9")

    status = version_check.get_update_status()

    assert status["current_version"] == version_check.__version__
    assert status["latest_version"] == "9.9.9"
    assert status["update_available"] is True
    assert status["checked"] is True
    assert status["notifications_enabled"] is True
    assert "pip install --upgrade pretorin" in status["prompt"]


def test_get_update_status_respects_opt_out(
    monkeypatch: MonkeyPatch,
    isolated_update_paths: Path,
) -> None:
    monkeypatch.setenv(config_module.ENV_DISABLE_UPDATE_CHECK, "1")

    status = version_check.get_update_status()

    assert status["notifications_enabled"] is False
    assert status["checked"] is False
    assert status["update_available"] is False
    assert status["prompt"] is None
