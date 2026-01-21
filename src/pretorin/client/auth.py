"""Authentication and credential management for Pretorin CLI."""

from __future__ import annotations

from pretorin.client.config import Config


def get_credentials() -> tuple[str | None, str]:
    """Get stored credentials.

    Returns:
        Tuple of (api_key, api_base_url). api_key may be None if not configured.
    """
    config = Config()
    return config.api_key, config.api_base_url


def store_credentials(api_key: str, api_base_url: str | None = None) -> None:
    """Store credentials to config file.

    Args:
        api_key: The API key to store.
        api_base_url: Optional custom API base URL.
    """
    config = Config()
    config.api_key = api_key
    if api_base_url:
        config.api_base_url = api_base_url


def clear_credentials() -> None:
    """Clear all stored credentials."""
    config = Config()
    config.clear()


def is_authenticated() -> bool:
    """Check if credentials are configured."""
    config = Config()
    return config.is_configured
