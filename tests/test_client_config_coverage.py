"""Coverage tests for src/pretorin/client/config.py.

Targets missing lines: _as_bool, Config properties (platform_api_base_url,
model_api_base_url, active_system_id setter, active_framework_id setter,
api_base_url setter, openai properties, codex paths, etc.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pretorin.client import config as config_module
from pretorin.client.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_MODEL_API_BASE_URL,
    DEFAULT_PLATFORM_API_BASE_URL,
    Config,
    _as_bool,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect config reads/writes to a temporary directory."""
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    for key in (
        "PRETORIN_API_KEY",
        "PRETORIN_API_BASE_URL",
        "PRETORIN_PLATFORM_API_BASE_URL",
        "PRETORIN_MODEL_API_BASE_URL",
        "PRETORIN_DISABLE_UPDATE_CHECK",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    return tmp_path


# ---------------------------------------------------------------------------
# _as_bool
# ---------------------------------------------------------------------------


class TestAsBool:
    def test_true_bool(self):
        assert _as_bool(True) is True

    def test_false_bool(self):
        assert _as_bool(False) is False

    def test_none_returns_false(self):
        assert _as_bool(None) is False

    def test_string_one(self):
        assert _as_bool("1") is True

    def test_string_true(self):
        assert _as_bool("true") is True

    def test_string_yes(self):
        assert _as_bool("yes") is True

    def test_string_on(self):
        assert _as_bool("on") is True

    def test_string_zero(self):
        assert _as_bool("0") is False

    def test_string_false(self):
        assert _as_bool("false") is False

    def test_string_no(self):
        assert _as_bool("no") is False

    def test_uppercase_true(self):
        assert _as_bool("TRUE") is True

    def test_mixed_case_yes(self):
        assert _as_bool("Yes") is True


# ---------------------------------------------------------------------------
# Config.get with env var overrides
# ---------------------------------------------------------------------------


class TestConfigGetEnvOverrides:
    def test_api_key_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PRETORIN_API_KEY", "env-key-123")
        cfg = Config()
        assert cfg.get("api_key") == "env-key-123"

    def test_platform_api_base_url_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PRETORIN_PLATFORM_API_BASE_URL", "https://env.example/v1")
        cfg = Config()
        assert cfg.get("platform_api_base_url") == "https://env.example/v1"

    def test_legacy_api_base_url_env_fallback(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PRETORIN_API_BASE_URL", "https://legacy.example/v1")
        cfg = Config()
        assert cfg.get("api_base_url") == "https://legacy.example/v1"

    def test_model_api_base_url_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PRETORIN_MODEL_API_BASE_URL", "https://model.env/v1")
        cfg = Config()
        assert cfg.get("model_api_base_url") == "https://model.env/v1"


# ---------------------------------------------------------------------------
# Config.set, delete, clear
# ---------------------------------------------------------------------------


class TestConfigSetDeleteClear:
    def test_set_and_get_value(self, isolated_config: Path):
        cfg = Config()
        cfg.set("my_key", "my_value")
        cfg2 = Config()
        assert cfg2.get("my_key") == "my_value"

    def test_delete_existing_key_returns_true(self, isolated_config: Path):
        cfg = Config()
        cfg.set("removable", "yes")
        result = cfg.delete("removable")
        assert result is True
        assert cfg.get("removable") is None

    def test_delete_nonexistent_key_returns_false(self, isolated_config: Path):
        cfg = Config()
        result = cfg.delete("does_not_exist")
        assert result is False

    def test_clear_removes_all_config(self, isolated_config: Path):
        cfg = Config()
        cfg.set("key1", "val1")
        cfg.set("key2", "val2")
        cfg.clear()
        cfg2 = Config()
        assert cfg2.get("key1") is None
        assert cfg2.get("key2") is None

    def test_to_dict_returns_stored_config(self, isolated_config: Path):
        cfg = Config()
        cfg.set("dict_key", "dict_val")
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["dict_key"] == "dict_val"


# ---------------------------------------------------------------------------
# platform_api_base_url property
# ---------------------------------------------------------------------------


class TestPlatformApiBaseUrl:
    def test_default_when_nothing_configured(self, isolated_config: Path):
        cfg = Config()
        assert cfg.platform_api_base_url == DEFAULT_PLATFORM_API_BASE_URL

    def test_configured_value_takes_precedence(self, isolated_config: Path):
        cfg = Config()
        cfg.set("platform_api_base_url", "https://configured.example/v1")
        cfg2 = Config()
        assert cfg2.platform_api_base_url == "https://configured.example/v1"

    def test_legacy_api_base_url_fallback(self, isolated_config: Path):
        cfg = Config()
        cfg.set("api_base_url", "https://legacy-stored.example/v1")
        cfg2 = Config()
        assert cfg2.platform_api_base_url == "https://legacy-stored.example/v1"


# ---------------------------------------------------------------------------
# api_base_url setter (backward-compatible alias)
# ---------------------------------------------------------------------------


class TestApiBaseUrlSetter:
    def test_api_base_url_setter_updates_platform_key(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("PRETORIN_PLATFORM_API_BASE_URL", raising=False)
        monkeypatch.delenv("PRETORIN_API_BASE_URL", raising=False)
        cfg = Config()
        cfg.api_base_url = "https://via-alias.example/v1"
        cfg2 = Config()
        assert cfg2.platform_api_base_url == "https://via-alias.example/v1"
        assert cfg2.api_base_url == "https://via-alias.example/v1"


# ---------------------------------------------------------------------------
# model_api_base_url property
# ---------------------------------------------------------------------------


class TestModelApiBaseUrl:
    def test_default_when_nothing_configured(self, isolated_config: Path):
        cfg = Config()
        assert cfg.model_api_base_url == DEFAULT_MODEL_API_BASE_URL

    def test_configured_model_api_base_url(self, isolated_config: Path):
        cfg = Config()
        cfg.set("model_api_base_url", "https://model.configured/v1")
        cfg2 = Config()
        assert cfg2.model_api_base_url == "https://model.configured/v1"

    def test_legacy_harness_base_url_fallback(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("PRETORIN_MODEL_API_BASE_URL", raising=False)
        cfg = Config()
        cfg.set("harness_base_url", "https://harness.legacy/v1")
        cfg2 = Config()
        assert cfg2.model_api_base_url == "https://harness.legacy/v1"

    def test_legacy_codex_base_url_fallback(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("PRETORIN_MODEL_API_BASE_URL", raising=False)
        cfg = Config()
        cfg.set("codex_base_url", "https://codex.legacy/v1")
        cfg2 = Config()
        assert cfg2.model_api_base_url == "https://codex.legacy/v1"

    def test_model_api_base_url_setter(self, isolated_config: Path):
        cfg = Config()
        cfg.model_api_base_url = "https://model.setter/v1"
        cfg2 = Config()
        assert cfg2.model_api_base_url == "https://model.setter/v1"


# ---------------------------------------------------------------------------
# active_system_id / active_framework_id setters
# ---------------------------------------------------------------------------


class TestActiveContextSetters:
    def test_active_system_id_setter_with_value(self, isolated_config: Path):
        cfg = Config()
        cfg.active_system_id = "sys-abc"
        assert cfg.active_system_id == "sys-abc"

    def test_active_system_id_setter_with_none_deletes_key(self, isolated_config: Path):
        cfg = Config()
        cfg.set("active_system_id", "sys-to-delete")
        cfg.active_system_id = None
        assert cfg.active_system_id is None

    def test_active_framework_id_setter_with_value(self, isolated_config: Path):
        cfg = Config()
        cfg.active_framework_id = "fedramp-moderate"
        assert cfg.active_framework_id == "fedramp-moderate"

    def test_active_framework_id_setter_with_none_deletes_key(self, isolated_config: Path):
        cfg = Config()
        cfg.set("active_framework_id", "framework-to-delete")
        cfg.active_framework_id = None
        assert cfg.active_framework_id is None


# ---------------------------------------------------------------------------
# OpenAI properties
# ---------------------------------------------------------------------------


class TestOpenAIProperties:
    def test_openai_api_key_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        cfg = Config()
        assert cfg.openai_api_key == "sk-env-key"

    def test_openai_api_key_from_config(self, isolated_config: Path):
        cfg = Config()
        cfg.set("openai_api_key", "sk-stored-key")
        cfg2 = Config()
        assert cfg2.openai_api_key == "sk-stored-key"

    def test_openai_api_key_env_overrides_config(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-wins")
        cfg = Config()
        cfg.set("openai_api_key", "sk-config-loses")
        assert cfg.openai_api_key == "sk-env-wins"

    def test_openai_base_url_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://custom-openai.example/v1")
        cfg = Config()
        assert cfg.openai_base_url == "https://custom-openai.example/v1"

    def test_openai_base_url_from_config(self, isolated_config: Path):
        cfg = Config()
        cfg.set("openai_base_url", "https://stored-openai.example/v1")
        cfg2 = Config()
        assert cfg2.openai_base_url == "https://stored-openai.example/v1"

    def test_openai_model_from_env(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        cfg = Config()
        assert cfg.openai_model == "gpt-4-turbo"

    def test_openai_model_from_config(self, isolated_config: Path):
        cfg = Config()
        cfg.set("openai_model", "gpt-3.5-turbo")
        cfg2 = Config()
        assert cfg2.openai_model == "gpt-3.5-turbo"

    def test_openai_model_default_is_gpt4o(self, isolated_config: Path):
        cfg = Config()
        assert cfg.openai_model == "gpt-4o"


# ---------------------------------------------------------------------------
# codex_home and codex_bin_dir
# ---------------------------------------------------------------------------


class TestCodexPaths:
    def test_codex_home_is_under_config_dir(self, isolated_config: Path):
        cfg = Config()
        assert cfg.codex_home == config_module.CONFIG_DIR / "codex"

    def test_codex_bin_dir_is_under_config_dir(self, isolated_config: Path):
        cfg = Config()
        assert cfg.codex_bin_dir == config_module.CONFIG_DIR / "bin"


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


class TestIsConfigured:
    def test_is_configured_true_when_api_key_set(self, isolated_config: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("PRETORIN_API_KEY", "some-key")
        cfg = Config()
        assert cfg.is_configured is True

    def test_is_configured_false_when_no_api_key(self, isolated_config: Path):
        cfg = Config()
        assert cfg.is_configured is False


# ---------------------------------------------------------------------------
# Loading invalid JSON
# ---------------------------------------------------------------------------


class TestInvalidJsonFile:
    def test_invalid_json_falls_back_to_empty_config(self, isolated_config: Path):
        config_file = isolated_config / "config.json"
        config_file.write_text("{invalid json!!!")
        cfg = Config()
        assert cfg.to_dict() == {}
