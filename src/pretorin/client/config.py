"""Configuration file management for Pretorin CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_API_BASE_URL = "https://platform.pretorin.com/api/v1"
CONFIG_DIR = Path.home() / ".pretorin"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Environment variable names
ENV_API_KEY = "PRETORIN_API_KEY"
ENV_API_BASE_URL = "PRETORIN_API_BASE_URL"


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
        elif key == "api_base_url":
            env_value = os.environ.get(ENV_API_BASE_URL)
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
    def api_base_url(self) -> str:
        """Get the API base URL (env var takes precedence)."""
        return self.get("api_base_url", DEFAULT_API_BASE_URL)

    @api_base_url.setter
    def api_base_url(self, value: str) -> None:
        """Set the API base URL."""
        self.set("api_base_url", value)

    @property
    def is_configured(self) -> bool:
        """Check if the CLI is configured with an API key."""
        return self.api_key is not None

    def to_dict(self) -> dict[str, Any]:
        """Return all stored config as a dictionary."""
        return dict(self._config)
