"""Async API client for Pretorin API."""

from __future__ import annotations

from typing import Any

import httpx

from pretorin.client.config import Config
from pretorin.client.models import (
    ComplianceArtifact,
    ControlContext,
    ControlDetail,
    ControlFamilyDetail,
    ControlFamilySummary,
    ControlImplementationResponse,
    ControlMetadata,
    ControlReferences,
    ControlSummary,
    DocumentRequirementList,
    EvidenceCreate,
    EvidenceItemResponse,
    FrameworkList,
    FrameworkMetadata,
    MonitoringEventCreate,
    NarrativeResponse,
    ScopeResponse,
    SystemDetail,
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
                timeout=60.0,
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
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise PretorianClientError(
                f"Could not connect to {self._api_base_url}{path} — "
                f"is the API reachable? ({exc})",
            ) from exc
        except httpx.TimeoutException as exc:
            raise PretorianClientError(
                f"Request timed out connecting to {self._api_base_url}{path} ({exc})",
            ) from exc
        except httpx.HTTPError as exc:
            raise PretorianClientError(
                f"HTTP error contacting {self._api_base_url}{path}: {exc}",
            ) from exc

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
            family_id: ID of the control family.

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
            control_id: ID of the control.

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

    # =========================================================================
    # System Endpoints
    # =========================================================================

    async def list_systems(self) -> list[dict[str, Any]]:
        """List all systems for the current user/organization.

        Returns:
            List of system dictionaries.
        """
        data = await self._request("GET", "/systems")
        if isinstance(data, list):
            return data
        # Handle paginated response
        return data.get("systems", data.get("items", []))

    async def get_system(self, system_id: str) -> SystemDetail:
        """Get detailed information about a system.

        Args:
            system_id: ID of the system.

        Returns:
            SystemDetail with full system information.
        """
        data = await self._request("GET", f"/systems/{system_id}")
        return SystemDetail(**data)

    async def get_system_compliance_status(self, system_id: str) -> dict[str, Any]:
        """Get compliance status for a system.

        Args:
            system_id: ID of the system.

        Returns:
            Dictionary with compliance status per framework.
        """
        data = await self._request("GET", f"/systems/{system_id}/compliance-status")
        return data

    # =========================================================================
    # Evidence Endpoints
    # =========================================================================

    async def list_evidence(
        self,
        system_id: str | None = None,
        control_id: str | None = None,
        framework_id: str | None = None,
        limit: int = 20,
    ) -> list[EvidenceItemResponse]:
        """Search/list evidence items for a system.

        Args:
            system_id: System ID (required for system-scoped queries).
            control_id: Optional control filter.
            framework_id: Optional framework filter.
            limit: Maximum results to return.

        Returns:
            List of evidence items.
        """
        params: dict[str, Any] = {"limit": limit}
        if control_id:
            params["control_id"] = control_id
        if framework_id:
            params["framework_id"] = framework_id

        path = f"/systems/{system_id}/evidence" if system_id else "/evidence"
        data = await self._request("GET", path, params=params)
        items = data if isinstance(data, list) else data.get("items", data.get("evidence", []))
        return [EvidenceItemResponse(**item) for item in items]

    async def get_evidence(self, evidence_id: str) -> EvidenceItemResponse:
        """Get a specific evidence item.

        Args:
            evidence_id: ID of the evidence item.

        Returns:
            Evidence item details.
        """
        data = await self._request("GET", f"/evidence/{evidence_id}")
        return EvidenceItemResponse(**data)

    async def create_evidence(
        self,
        system_id: str,
        evidence: EvidenceCreate,
    ) -> dict[str, Any]:
        """Create a new evidence item for a system.

        Args:
            system_id: System ID to associate evidence with.
            evidence: Evidence data.

        Returns:
            Created evidence response.
        """
        payload = evidence.model_dump(exclude_none=True)
        data = await self._request(
            "POST",
            f"/systems/{system_id}/evidence",
            json=payload,
        )
        return data

    async def link_evidence_to_control(
        self,
        evidence_id: str,
        control_id: str,
        system_id: str | None = None,
        framework_id: str | None = None,
    ) -> dict[str, Any]:
        """Link an evidence item to a control.

        Args:
            evidence_id: ID of the evidence item.
            control_id: ID of the control to link to.
            system_id: System ID for routing.
            framework_id: Optional framework context.

        Returns:
            Link result.
        """
        payload: dict[str, Any] = {"control_id": control_id}
        if framework_id:
            payload["framework_id"] = framework_id
        path = f"/systems/{system_id}/evidence/{evidence_id}/link" if system_id else f"/evidence/{evidence_id}/link"
        data = await self._request("POST", path, json=payload)
        return data

    # =========================================================================
    # Narrative Endpoints
    # =========================================================================

    async def get_narrative(
        self,
        system_id: str,
        control_id: str,
        framework_id: str | None = None,
    ) -> NarrativeResponse:
        """Get an existing narrative for a control.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            framework_id: Optional framework filter.

        Returns:
            Narrative response.
        """
        params: dict[str, Any] = {}
        if framework_id:
            params["framework_id"] = framework_id
        data = await self._request(
            "GET",
            f"/systems/{system_id}/controls/{control_id}/narrative",
            params=params,
        )
        return NarrativeResponse(**data)

    # =========================================================================
    # Control Implementation Endpoints
    # =========================================================================

    async def get_control_implementation(
        self,
        system_id: str,
        control_id: str,
        framework_id: str | None = None,
    ) -> ControlImplementationResponse:
        """Get implementation details for a control in a system.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            framework_id: Optional framework filter.

        Returns:
            Control implementation details.
        """
        params: dict[str, Any] = {}
        if framework_id:
            params["framework_id"] = framework_id
        data = await self._request(
            "GET",
            f"/systems/{system_id}/controls/{control_id}",
            params=params,
        )
        return ControlImplementationResponse(**data)

    async def get_control_context(
        self,
        system_id: str,
        control_id: str,
        framework_id: str,
    ) -> ControlContext:
        """Get rich context for a control including AI guidance and implementation.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            framework_id: Framework ID.

        Returns:
            ControlContext with combined OSCAL + implementation data.
        """
        data = await self._request(
            "GET",
            f"/systems/{system_id}/controls/{control_id}/context",
            params={"framework_id": framework_id},
        )
        return ControlContext(**data)

    async def update_narrative(
        self,
        system_id: str,
        control_id: str,
        narrative: str,
        framework_id: str,
        is_ai_generated: bool = False,
    ) -> dict[str, Any]:
        """Push a narrative update for a control.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            narrative: Narrative text.
            framework_id: Framework ID.
            is_ai_generated: Whether the narrative was AI-generated.

        Returns:
            Updated control implementation data.
        """
        data = await self._request(
            "POST",
            f"/systems/{system_id}/controls/{control_id}/narrative",
            params={"framework_id": framework_id},
            json={"narrative": narrative, "is_ai_generated": is_ai_generated},
        )
        return data

    async def get_scope(self, system_id: str) -> ScopeResponse:
        """Get system scope/policy information.

        Args:
            system_id: ID of the system.

        Returns:
            ScopeResponse with scope details.
        """
        data = await self._request("GET", f"/systems/{system_id}/scope")
        return ScopeResponse(**data)

    async def add_control_note(
        self,
        system_id: str,
        control_id: str,
        content: str,
        framework_id: str,
        source: str = "cli",
    ) -> dict[str, Any]:
        """Add a note to a control implementation.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            content: Note content.
            framework_id: Framework ID (required by the API).
            source: Note source identifier.

        Returns:
            Created note response.
        """
        payload = {"content": content, "source": source}
        data = await self._request(
            "POST",
            f"/systems/{system_id}/controls/{control_id}/notes",
            params={"framework_id": framework_id},
            json=payload,
        )
        return data

    async def update_control_status(
        self,
        system_id: str,
        control_id: str,
        status: str,
        framework_id: str | None = None,
    ) -> dict[str, Any]:
        """Update the implementation status of a control.

        Args:
            system_id: ID of the system.
            control_id: ID of the control.
            status: New status value.
            framework_id: Optional framework context.

        Returns:
            Updated control response.
        """
        params: dict[str, Any] = {}
        if framework_id:
            params["framework_id"] = framework_id
        data = await self._request(
            "POST",
            f"/systems/{system_id}/controls/{control_id}/status",
            params=params,
            json={"status": status},
        )
        return data

    # =========================================================================
    # Monitoring Endpoints
    # =========================================================================

    async def create_monitoring_event(
        self,
        system_id: str,
        event: MonitoringEventCreate,
    ) -> dict[str, Any]:
        """Create a monitoring event for a system.

        Args:
            system_id: ID of the system.
            event: Event data.

        Returns:
            Created event response.
        """
        data = await self._request(
            "POST",
            f"/systems/{system_id}/monitoring/events",
            json=event.model_dump(exclude_none=True),
        )
        return data
