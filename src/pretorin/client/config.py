"""Configuration file management for Pretorin CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PLATFORM_API_BASE_URL = "https://platform.pretorin.com/api/v1/public"
DEFAULT_MODEL_API_BASE_URL = "https://platform.pretorin.com/v1"
CONFIG_DIR = Path.home() / ".pretorin"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Environment variable names
ENV_API_KEY = "PRETORIN_API_KEY"
# Backward-compatible alias for platform API URL
ENV_API_BASE_URL = "PRETORIN_API_BASE_URL"
ENV_PLATFORM_API_BASE_URL = "PRETORIN_PLATFORM_API_BASE_URL"
ENV_MODEL_API_BASE_URL = "PRETORIN_MODEL_API_BASE_URL"
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_BASE_URL = "OPENAI_BASE_URL"
ENV_OPENAI_MODEL = "OPENAI_MODEL"


class Config:
    """Manages Pretorin CLI configuration."""

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
    def active_system_id(self) -> str | None:
        """Get the active system ID for context commands."""
        return self.get("active_system_id")

    @active_system_id.setter
    def active_system_id(self, value: str | None) -> None:
        """Set the active system ID."""
        if value is None:
            self.delete("active_system_id")
        else:
            self.set("active_system_id", value)

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
        """Get the OpenAI model (env var takes precedence)."""
        env = os.environ.get(ENV_OPENAI_MODEL)
        return env if env else self.get("openai_model", "gpt-4o")

    def to_dict(self) -> dict[str, Any]:
        """Return all stored config as a dictionary."""
        return dict(self._config)
