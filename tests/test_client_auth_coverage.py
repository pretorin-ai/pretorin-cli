"""Tests for src/pretorin/client/auth.py.

Covers get_credentials, store_credentials, clear_credentials, and is_authenticated
using isolated temporary config paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pretorin.client import config as config_module
from pretorin.client.auth import (
    _derive_model_api_base_url,
    clear_credentials,
    get_credentials,
    is_authenticated,
    store_credentials,
)

# ---------------------------------------------------------------------------
# Fixture: redirect all config reads/writes to a tmp directory
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect Config file I/O to a temporary directory."""
    config_dir = tmp_path / ".pretorin"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    # Ensure the env var does not override stored credentials
    monkeypatch.delenv(config_module.ENV_API_KEY, raising=False)
    return config_file


# ---------------------------------------------------------------------------
# store_credentials + get_credentials
# ---------------------------------------------------------------------------


def test_store_and_get_credentials(isolated_config: Path) -> None:
    store_credentials("test-key-123")
    key, url = get_credentials()
    assert key == "test-key-123"


def test_get_credentials_returns_default_url_when_not_set(isolated_config: Path) -> None:
    store_credentials("my-key")
    _, url = get_credentials()
    assert url == config_module.DEFAULT_PLATFORM_API_BASE_URL


def test_store_credentials_with_custom_url(isolated_config: Path) -> None:
    store_credentials("my-key", api_base_url="https://custom.example.com/api/v1")
    key, url = get_credentials()
    assert key == "my-key"
    assert url == "https://custom.example.com/api/v1"


def test_store_credentials_with_public_url_sets_matching_model_url(isolated_config: Path) -> None:
    store_credentials("my-key", api_base_url="https://custom.example.com/api/v1/public")

    cfg = config_module.Config()
    assert cfg.model_api_base_url == "https://custom.example.com/v1"


def test_derive_model_api_base_url_handles_non_api_root() -> None:
    assert _derive_model_api_base_url("https://custom.example.com") == "https://custom.example.com/v1"


def test_store_credentials_without_url_does_not_overwrite_default(isolated_config: Path) -> None:
    store_credentials("key-no-url")
    _, url = get_credentials()
    # No custom URL provided, should fall back to the default
    assert url == config_module.DEFAULT_PLATFORM_API_BASE_URL


def test_store_credentials_without_url_resets_custom_endpoint_to_default(isolated_config: Path) -> None:
    store_credentials("first-key", api_base_url="https://custom.example.com/api/v1/public")

    store_credentials("second-key")

    cfg = config_module.Config()
    assert cfg.api_base_url == config_module.DEFAULT_PLATFORM_API_BASE_URL
    assert cfg.model_api_base_url == config_module.DEFAULT_MODEL_API_BASE_URL


def test_store_credentials_clears_active_context_when_api_key_changes(isolated_config: Path) -> None:
    cfg = config_module.Config()
    cfg.active_system_id = "system-local"
    cfg.active_framework_id = "fedramp-moderate"
    cfg.api_base_url = "http://localhost:8000/api/v1/public"
    cfg.model_api_base_url = "http://localhost:8000/v1"
    cfg.api_key = "old-key"

    store_credentials("new-key", api_base_url="https://platform.pretorin.com/api/v1/public")

    reloaded = config_module.Config()
    assert reloaded.active_system_id is None
    assert reloaded.active_framework_id is None


def test_store_credentials_clears_active_context_when_api_url_changes(isolated_config: Path) -> None:
    cfg = config_module.Config()
    cfg.active_system_id = "system-local"
    cfg.active_framework_id = "fedramp-moderate"
    cfg.api_base_url = "http://localhost:8000/api/v1/public"
    cfg.model_api_base_url = "http://localhost:8000/v1"
    cfg.api_key = "same-key"

    store_credentials("same-key", api_base_url="https://platform.pretorin.com/api/v1/public")

    reloaded = config_module.Config()
    assert reloaded.active_system_id is None
    assert reloaded.active_framework_id is None


def test_store_credentials_preserves_active_context_when_credentials_unchanged(isolated_config: Path) -> None:
    store_credentials("same-key", api_base_url="https://platform.pretorin.com/api/v1/public")

    cfg = config_module.Config()
    cfg.active_system_id = "system-prod"
    cfg.active_framework_id = "soc2"

    store_credentials("same-key", api_base_url="https://platform.pretorin.com/api/v1/public")

    reloaded = config_module.Config()
    assert reloaded.active_system_id == "system-prod"
    assert reloaded.active_framework_id == "soc2"


def test_store_credentials_persists_to_file(isolated_config: Path) -> None:
    store_credentials("persisted-key")
    # The config file must have been created
    assert isolated_config.exists()


# ---------------------------------------------------------------------------
# clear_credentials
# ---------------------------------------------------------------------------


def test_clear_credentials(isolated_config: Path) -> None:
    store_credentials("test-key-123")
    clear_credentials()
    assert not is_authenticated()


def test_clear_credentials_when_none_stored(isolated_config: Path) -> None:
    # Should not raise even if nothing was stored
    clear_credentials()
    assert not is_authenticated()


def test_get_credentials_returns_none_after_clear(isolated_config: Path) -> None:
    store_credentials("clear-me")
    clear_credentials()
    key, _ = get_credentials()
    assert key is None


# ---------------------------------------------------------------------------
# is_authenticated
# ---------------------------------------------------------------------------


def test_is_authenticated_true_when_key_stored(isolated_config: Path) -> None:
    store_credentials("valid-api-key")
    assert is_authenticated() is True


def test_is_authenticated_false_when_no_key(isolated_config: Path) -> None:
    assert is_authenticated() is False


def test_is_authenticated_false_after_clear(isolated_config: Path) -> None:
    store_credentials("will-be-cleared")
    clear_credentials()
    assert is_authenticated() is False


def test_is_authenticated_via_env_var(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Environment variable takes precedence; is_authenticated returns True."""
    config_dir = tmp_path / ".pretorin"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    monkeypatch.setenv(config_module.ENV_API_KEY, "env-key-value")

    assert is_authenticated() is True
