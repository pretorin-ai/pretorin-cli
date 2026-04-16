"""Configuration file management for Pretorin CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PLATFORM_API_BASE_URL = "https://platform.pretorin.com/api/v1/public"
DEFAULT_MODEL_API_BASE_URL = "https://platform.pretorin.com/api/v1/public/model"
CONFIG_DIR = Path.home() / ".pretorin"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Environment variable names
ENV_API_KEY = "PRETORIN_API_KEY"
# Backward-compatible alias for platform API URL
ENV_API_BASE_URL = "PRETORIN_API_BASE_URL"
ENV_PLATFORM_API_BASE_URL = "PRETORIN_PLATFORM_API_BASE_URL"
ENV_MODEL_API_BASE_URL = "PRETORIN_MODEL_API_BASE_URL"
ENV_DISABLE_UPDATE_CHECK = "PRETORIN_DISABLE_UPDATE_CHECK"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_BASE_URL = "OPENAI_BASE_URL"
ENV_OPENAI_MODEL = "OPENAI_MODEL"
ENV_SYSTEM_ID = "PRETORIN_SYSTEM_ID"
ENV_FRAMEWORK_ID = "PRETORIN_FRAMEWORK_ID"
ENV_SOURCE_PROVIDERS = "PRETORIN_SOURCE_PROVIDERS"


def _as_bool(value: Any) -> bool:
    """Interpret common truthy string values."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Manages Pretorin CLI configuration."""

    # Class-level cache so all Config instances share the fetched org model.
    _org_cli_model: str | None = None

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._config = {}
        else:
            self._config = {}

    def _save(self) -> None:
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=2)
        # Set restrictive permissions on config file (contains API key)
        CONFIG_FILE.chmod(0o600)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Environment variables take precedence over stored config.
        """
        # Check environment variables first
        if key == "api_key":
            env_value = os.environ.get(ENV_API_KEY)
            if env_value:
                return env_value
        elif key in {"api_base_url", "platform_api_base_url"}:
            env_value = os.environ.get(ENV_PLATFORM_API_BASE_URL) or os.environ.get(ENV_API_BASE_URL)
            if env_value:
                return env_value
        elif key in {"model_api_base_url", "harness_base_url", "codex_base_url"}:
            env_value = os.environ.get(ENV_MODEL_API_BASE_URL)
            if env_value:
                return env_value
        elif key == "disable_update_check":
            env_value = os.environ.get(ENV_DISABLE_UPDATE_CHECK)
            if env_value is not None:
                return env_value
        elif key == "active_system_id":
            env_value = os.environ.get(ENV_SYSTEM_ID)
            if env_value:
                return env_value
        elif key == "active_framework_id":
            env_value = os.environ.get(ENV_FRAMEWORK_ID)
            if env_value:
                return env_value
        elif key == "source_providers":
            env_value = os.environ.get(ENV_SOURCE_PROVIDERS)
            if env_value:
                try:
                    return json.loads(env_value)
                except json.JSONDecodeError:
                    pass

        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save to file."""
        self._config[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        """Delete a configuration value. Returns True if key existed."""
        if key in self._config:
            del self._config[key]
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Clear all configuration."""
        self._config = {}
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

    @property
    def api_key(self) -> str | None:
        """Get the API key (env var takes precedence)."""
        return self.get("api_key")

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the API key."""
        self.set("api_key", value)

    @property
    def platform_api_base_url(self) -> str:
        """Get the Pretorin platform REST API base URL."""
        configured = self.get("platform_api_base_url")
        if configured:
            return str(configured)
        legacy = self.get("api_base_url")
        if legacy:
            return str(legacy)
        return DEFAULT_PLATFORM_API_BASE_URL

    @platform_api_base_url.setter
    def platform_api_base_url(self, value: str) -> None:
        """Set the Pretorin platform REST API base URL."""
        self.set("platform_api_base_url", value)
        # Keep legacy key updated for compatibility with older installations.
        self.set("api_base_url", value)

    @property
    def api_base_url(self) -> str:
        """Backward-compatible alias for platform_api_base_url."""
        return self.platform_api_base_url

    @api_base_url.setter
    def api_base_url(self, value: str) -> None:
        """Set the API base URL (backward-compatible alias)."""
        self.platform_api_base_url = value

    @property
    def model_api_base_url(self) -> str:
        """Get the model provider base URL used by harness integrations."""
        configured = self.get("model_api_base_url")
        if configured:
            return str(configured)
        # Backward-compatible keys used in previous harness prototypes.
        legacy_harness = self.get("harness_base_url")
        if legacy_harness:
            return str(legacy_harness)
        legacy_codex = self.get("codex_base_url")
        if legacy_codex:
            return str(legacy_codex)
        return DEFAULT_MODEL_API_BASE_URL

    @model_api_base_url.setter
    def model_api_base_url(self, value: str) -> None:
        """Set the model provider base URL used by harness integrations."""
        self.set("model_api_base_url", value)

    @property
    def context_api_base_url(self) -> str | None:
        """Get the API base URL that was active when the context was set."""
        return self.get("context_api_base_url")

    @context_api_base_url.setter
    def context_api_base_url(self, value: str | None) -> None:
        """Set the API base URL captured at context-set time."""
        if value is None:
            self.delete("context_api_base_url")
        else:
            self.set("context_api_base_url", value)

    def check_context_environment(self) -> str | None:
        """Compare stored context URL against the current platform URL.

        Returns ``None`` when the environment matches (or when no stored URL
        exists for backward compatibility).  Returns a human-readable error
        string when the URLs diverge.
        """
        stored = self.context_api_base_url
        if not stored:
            return None
        current = self.platform_api_base_url
        if stored.rstrip("/") == current.rstrip("/"):
            return None
        return (
            f"Context was set against '{stored}' but the current API environment is "
            f"'{current}'. Run 'pretorin context set' to update your context."
        )

    @property
    def active_system_id(self) -> str | None:
        """Get the active system ID for context commands."""
        return self.get("active_system_id")

    @active_system_id.setter
    def active_system_id(self, value: str | None) -> None:
        """Set the active system ID."""
        if value is None:
            self.delete("active_system_id")
            self.delete("active_system_name")
            self.delete("context_api_base_url")
        else:
            self.set("active_system_id", value)

    @property
    def active_system_name(self) -> str | None:
        """Get the cached active system name for friendlier context output."""
        return self.get("active_system_name")

    @active_system_name.setter
    def active_system_name(self, value: str | None) -> None:
        """Set the cached active system name."""
        if value is None:
            self.delete("active_system_name")
        else:
            self.set("active_system_name", value)

    @property
    def active_framework_id(self) -> str | None:
        """Get the active framework ID for context commands."""
        return self.get("active_framework_id")

    @active_framework_id.setter
    def active_framework_id(self, value: str | None) -> None:
        """Set the active framework ID."""
        if value is None:
            self.delete("active_framework_id")
        else:
            self.set("active_framework_id", value)

    @property
    def source_providers(self) -> list[dict[str, Any]] | None:
        """Source provider config. None means use auto-detect defaults."""
        return self.get("source_providers")

    @property
    def disable_update_check(self) -> bool:
        """Disable passive update notifications."""
        return _as_bool(self.get("disable_update_check", False))

    @property
    def is_configured(self) -> bool:
        """Check if the CLI is configured with an API key."""
        return self.api_key is not None

    @property
    def openai_api_key(self) -> str | None:
        """Get the OpenAI API key (env var takes precedence)."""
        env = os.environ.get(ENV_OPENAI_API_KEY)
        return env if env else self.get("openai_api_key")

    @property
    def openai_base_url(self) -> str | None:
        """Get the OpenAI base URL (env var takes precedence)."""
        env = os.environ.get(ENV_OPENAI_BASE_URL)
        return env if env else self.get("openai_base_url")

    @property
    def openai_model(self) -> str:
        """Get the OpenAI model.

        Precedence:
        1. ``OPENAI_MODEL`` env var
        2. Local ``openai_model`` config key
        3. Org AI settings fetched from the platform (cached)
        4. ``"gpt-4o"`` default
        """
        env = os.environ.get(ENV_OPENAI_MODEL)
        if env:
            return env
        local = self.get("openai_model")
        if local:
            return local
        if self._org_cli_model is not None:
            return self._org_cli_model
        return "gpt-4o"

    @classmethod
    def set_org_cli_model(cls, model: str) -> None:
        """Cache the org's CLI model fetched from the platform API."""
        cls._org_cli_model = model

    @property
    def codex_home(self) -> Path:
        """Isolated Codex home directory managed by Pretorin."""
        return CONFIG_DIR / "codex"

    @property
    def codex_bin_dir(self) -> Path:
        """Directory for managed Codex binaries."""
        return CONFIG_DIR / "bin"

    def to_dict(self) -> dict[str, Any]:
        """Return all stored config as a dictionary."""
        return dict(self._config)
