"""Tests for configuration defaults and endpoint URL precedence."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from pretorin.client import config as config_module


@pytest.fixture
def isolated_config_paths(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect config reads/writes to a temporary directory."""
    config_dir = tmp_path / ".pretorin"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    return config_file


def test_default_endpoint_urls(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_MODEL_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    assert cfg.platform_api_base_url == config_module.DEFAULT_PLATFORM_API_BASE_URL
    assert cfg.api_base_url == config_module.DEFAULT_PLATFORM_API_BASE_URL
    assert cfg.model_api_base_url == config_module.DEFAULT_MODEL_API_BASE_URL


def test_platform_url_env_precedence(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.setenv(config_module.ENV_API_BASE_URL, "https://legacy.example/v1")
    monkeypatch.setenv(config_module.ENV_PLATFORM_API_BASE_URL, "https://platform.example/v1")

    cfg = config_module.Config()
    assert cfg.platform_api_base_url == "https://platform.example/v1"
    assert cfg.api_base_url == "https://platform.example/v1"


def test_model_url_env_overrides_legacy_keys(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.setenv(config_module.ENV_MODEL_API_BASE_URL, "https://model.env.example/v1")

    cfg = config_module.Config()
    cfg.set("harness_base_url", "https://legacy-harness.example/v1")
    cfg.set("codex_base_url", "https://legacy-codex.example/v1")

    cfg_reloaded = config_module.Config()
    assert cfg_reloaded.model_api_base_url == "https://model.env.example/v1"


def test_model_url_falls_back_to_legacy_harness_key(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_MODEL_API_BASE_URL, raising=False)
    cfg = config_module.Config()
    cfg.set("harness_base_url", "https://legacy-harness.example/v1")

    cfg_reloaded = config_module.Config()
    assert cfg_reloaded.model_api_base_url == "https://legacy-harness.example/v1"


def test_model_url_prefers_model_key_over_legacy(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_MODEL_API_BASE_URL, raising=False)
    cfg = config_module.Config()
    cfg.set("harness_base_url", "https://legacy-harness.example/v1")
    cfg.set("model_api_base_url", "https://model-primary.example/v1")

    cfg_reloaded = config_module.Config()
    assert cfg_reloaded.model_api_base_url == "https://model-primary.example/v1"


def test_platform_setter_updates_legacy_api_alias(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)
    cfg = config_module.Config()

    cfg.platform_api_base_url = "https://platform.custom.example/v1"
    cfg_reloaded = config_module.Config()

    assert cfg_reloaded.platform_api_base_url == "https://platform.custom.example/v1"
    assert cfg_reloaded.get("platform_api_base_url") == "https://platform.custom.example/v1"
    assert cfg_reloaded.get("api_base_url") == "https://platform.custom.example/v1"


def test_api_base_url_alias_setter_updates_platform_key(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)
    cfg = config_module.Config()

    cfg.api_base_url = "https://alias.custom.example/v1"
    cfg_reloaded = config_module.Config()

    assert cfg_reloaded.api_base_url == "https://alias.custom.example/v1"
    assert cfg_reloaded.platform_api_base_url == "https://alias.custom.example/v1"
    assert cfg_reloaded.get("platform_api_base_url") == "https://alias.custom.example/v1"


# --- Environment-aware context validation ---


def test_check_context_environment_detects_mismatch(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    cfg.context_api_base_url = "https://localhost:8000/api/v1/public"
    # Current platform URL defaults to DEFAULT_PLATFORM_API_BASE_URL (prod)
    error = cfg.check_context_environment()
    assert error is not None
    assert "localhost:8000" in error
    assert config_module.DEFAULT_PLATFORM_API_BASE_URL in error


def test_check_context_environment_ok_when_matching(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    cfg.context_api_base_url = config_module.DEFAULT_PLATFORM_API_BASE_URL
    assert cfg.check_context_environment() is None


def test_check_context_environment_normalizes_trailing_slash(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    cfg.context_api_base_url = config_module.DEFAULT_PLATFORM_API_BASE_URL + "/"
    assert cfg.check_context_environment() is None


def test_check_context_environment_skips_when_no_stored_url(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    # No context_api_base_url set — backward compat
    assert cfg.check_context_environment() is None


def test_clearing_active_system_also_clears_context_url(
    monkeypatch: MonkeyPatch,
    isolated_config_paths: Path,
) -> None:
    monkeypatch.delenv(config_module.ENV_PLATFORM_API_BASE_URL, raising=False)
    monkeypatch.delenv(config_module.ENV_API_BASE_URL, raising=False)

    cfg = config_module.Config()
    cfg.set("active_system_id", "sys-1")
    cfg.context_api_base_url = "https://localhost:8000/api/v1/public"
    assert cfg.context_api_base_url is not None

    cfg.active_system_id = None
    cfg_reloaded = config_module.Config()
    assert cfg_reloaded.context_api_base_url is None
