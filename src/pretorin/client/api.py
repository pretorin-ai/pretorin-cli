"""Async API client for Pretorin API."""

from __future__ import annotations

from typing import Any

import httpx

from pretorin.client.config import Config
from pretorin.client.models import (
    ComplianceArtifact,
    ControlDetail,
    ControlFamilyDetail,
    ControlFamilySummary,
    ControlMetadata,
    ControlReferences,
    ControlSummary,
    DocumentRequirementList,
    FrameworkList,
    FrameworkMetadata,
)


class PretorianClientError(Exception):
    """Base exception for Pretorian client errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(PretorianClientError):
    """Raised when authentication fails."""

    pass


class NotFoundError(PretorianClientError):
    """Raised when a resource is not found."""

    pass


class PretorianClient:
    """Async client for the Pretorin API."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            api_key: API key for authentication. If not provided, will load from config.
            api_base_url: Base URL for the API. If not provided, will load from config.
        """
        config = Config()
        self._api_key = api_key or config.api_key
        self._api_base_url = (api_base_url or config.api_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """Check if the client has an API key configured."""
        return self._api_key is not None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers including authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "pretorin-cli/0.1.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._api_base_url,
                headers=self._get_headers(),
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> PretorianClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            data = response.json()
            # FastAPI returns {"detail": "message"} for errors
            if isinstance(data, dict):
                message = data.get("detail") or data.get("message") or str(data)
            else:
                message = str(data)
            details = data if isinstance(data, dict) else {}
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
            details = {}

        if response.status_code == 401:
            raise AuthenticationError(message, response.status_code, details)
        elif response.status_code == 403:
            raise AuthenticationError(f"Access denied: {message}", response.status_code, details)
        elif response.status_code == 404:
            raise NotFoundError(message, response.status_code, details)
        else:
            raise PretorianClientError(message, response.status_code, details)

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make an API request.

        Args:
            method: HTTP method.
            path: API path (relative to base URL).
            **kwargs: Additional arguments to pass to httpx.

        Returns:
            JSON response data.

        Raises:
            PretorianClientError: If the request fails.
        """
        client = await self._get_client()
        response = await client.request(method, path, **kwargs)

        if not response.is_success:
            self._handle_error(response)

        if response.status_code == 204:
            return {}

        return response.json()

    # =========================================================================
    # Auth / Validation
    # =========================================================================

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request.

        Returns:
            True if the API key is valid.

        Raises:
            AuthenticationError: If the API key is invalid.
        """
        if not self._api_key:
            raise AuthenticationError("No API key configured")

        # Use frameworks endpoint as a lightweight validation check
        await self._request("GET", "/frameworks")
        return True

    # =========================================================================
    # Framework Endpoints
    # =========================================================================

    async def list_frameworks(self) -> FrameworkList:
        """List all available compliance frameworks.

        Returns:
            FrameworkList containing all frameworks with summary info.
        """
        data = await self._request("GET", "/frameworks")
        return FrameworkList(**data)

    async def get_framework(self, framework_id: str) -> FrameworkMetadata:
        """Get detailed metadata about a specific framework.

        Args:
            framework_id: ID of the framework (e.g., nist-800-53-r5, fedramp-moderate)

        Returns:
            FrameworkMetadata with full framework details.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}")
        return FrameworkMetadata(**data)

    # =========================================================================
    # Control Family Endpoints
    # =========================================================================

    async def list_control_families(self, framework_id: str) -> list[ControlFamilySummary]:
        """List all control families for a framework.

        Args:
            framework_id: ID of the framework.

        Returns:
            List of control family summaries.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}/families")
        return [ControlFamilySummary(**item) for item in data]

    async def get_control_family(self, framework_id: str, family_id: str) -> ControlFamilyDetail:
        """Get detailed information about a control family.

        Args:
            framework_id: ID of the framework.
            family_id: ID of the control family (e.g., ac, au, cm).

        Returns:
            ControlFamilyDetail with family info and controls list.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}/families/{family_id}")
        return ControlFamilyDetail(**data)

    # =========================================================================
    # Control Endpoints
    # =========================================================================

    async def list_controls(
        self,
        framework_id: str,
        family_id: str | None = None,
    ) -> list[ControlSummary]:
        """List controls for a framework.

        Args:
            framework_id: ID of the framework.
            family_id: Optional filter by control family.

        Returns:
            List of control summaries.
        """
        params = {}
        if family_id:
            params["family_id"] = family_id

        data = await self._request("GET", f"/frameworks/{framework_id}/controls", params=params)
        return [ControlSummary(**item) for item in data]

    async def get_control(self, framework_id: str, control_id: str) -> ControlDetail:
        """Get detailed information about a specific control.

        Args:
            framework_id: ID of the framework.
            control_id: ID of the control (e.g., ac-1, ac-2).

        Returns:
            ControlDetail with full control information.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}/controls/{control_id}")
        return ControlDetail(**data)

    async def get_control_references(self, framework_id: str, control_id: str) -> ControlReferences:
        """Get reference data for a control including guidance and objectives.

        Args:
            framework_id: ID of the framework.
            control_id: ID of the control.

        Returns:
            ControlReferences with statement, guidance, objectives, etc.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}/controls/{control_id}/references")
        return ControlReferences(**data)

    async def get_controls_metadata(self, framework_id: str | None = None) -> dict[str, ControlMetadata]:
        """Get metadata for controls.

        Args:
            framework_id: Optional framework ID. If provided, returns metadata
                         for controls in that framework only. Otherwise returns
                         metadata for all controls across all frameworks.

        Returns:
            Dictionary mapping control IDs to their metadata.
        """
        if framework_id:
            path = f"/frameworks/{framework_id}/controls/metadata"
        else:
            path = "/frameworks/controls/metadata"

        data = await self._request("GET", path)
        return {k: ControlMetadata(**v) for k, v in data.items()}

    # =========================================================================
    # Document Requirements
    # =========================================================================

    async def get_document_requirements(self, framework_id: str) -> DocumentRequirementList:
        """Get document requirements for a framework.

        Args:
            framework_id: ID of the framework.

        Returns:
            DocumentRequirementList with explicit and implicit requirements.
        """
        data = await self._request("GET", f"/frameworks/{framework_id}/documents")
        return DocumentRequirementList(**data)

    # =========================================================================
    # Compliance Artifacts
    # =========================================================================

    async def submit_artifact(self, artifact: ComplianceArtifact) -> dict[str, Any]:
        """Submit a compliance artifact to the Pretorin platform.

        Args:
            artifact: The compliance artifact to submit.

        Returns:
            Dictionary containing artifact_id and URL.

        Raises:
            PretorianClientError: If the submission fails.
        """
        data = await self._request(
            "POST",
            "/artifacts",
            json=artifact.model_dump(),
        )
        return data
