"""Authentication and credential management for Pretorin CLI."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from pretorin.client.config import (
    DEFAULT_MODEL_API_BASE_URL,
    DEFAULT_PLATFORM_API_BASE_URL,
    Config,
)


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
    stored = config.to_dict()
    previous_api_key = stored.get("api_key")
    previous_api_base_url = stored.get("platform_api_base_url") or stored.get("api_base_url")

    resolved_api_base_url = api_base_url or DEFAULT_PLATFORM_API_BASE_URL
    resolved_model_api_base_url = (
        _derive_model_api_base_url(resolved_api_base_url) if api_base_url else DEFAULT_MODEL_API_BASE_URL
    )

    context_changed = previous_api_key != api_key or previous_api_base_url != resolved_api_base_url

    config.api_key = api_key
    config.api_base_url = resolved_api_base_url
    config.model_api_base_url = resolved_model_api_base_url

    if context_changed:
        config.active_system_id = None
        config.active_framework_id = None


def _derive_model_api_base_url(api_base_url: str) -> str:
    """Translate a public platform API URL into the matching model proxy URL."""
    parsed = urlsplit(api_base_url)
    path = parsed.path.rstrip("/")
    for suffix in ("/api/v1/public", "/api/v1"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    normalized_path = f"{path}/api/v1/public/model" if path else "/api/v1/public/model"
    return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def clear_credentials() -> None:
    """Clear all stored credentials."""
    config = Config()
    config.clear()


def is_authenticated() -> bool:
    """Check if credentials are configured."""
    config = Config()
    return config.is_configured
