"""Async API client for Pretorin Compliance API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from pretorin.client.config import Config, DEFAULT_API_BASE_URL
from pretorin.client.models import (
    APIError,
    ComplianceCheck,
    ComplianceReport,
    ReportListItem,
    UserInfo,
)


class PretorianClientError(Exception):
    """Base exception for Pretorian client errors."""

    def __init__(self, message: str, status_code: int | None = None, details: dict[str, Any] | None = None):
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
    """Async client for the Pretorin Compliance API."""

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

    async def __aenter__(self) -> "PretorianClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        try:
            data = response.json()
            error = APIError(**data)
            message = error.message
            details = error.details
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
            details = {}

        if response.status_code == 401:
            raise AuthenticationError(message, response.status_code, details)
        elif response.status_code == 404:
            raise NotFoundError(message, response.status_code, details)
        else:
            raise PretorianClientError(message, response.status_code, details)

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request.

        Args:
            method: HTTP method.
            path: API path.
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

    # Auth endpoints

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request.

        Returns:
            True if the API key is valid.

        Raises:
            AuthenticationError: If the API key is invalid.
        """
        if not self._api_key:
            raise AuthenticationError("No API key configured")

        await self._request("GET", "/v1/auth/validate")
        return True

    async def get_user_info(self) -> UserInfo:
        """Get information about the authenticated user.

        Returns:
            UserInfo with details about the current user/organization.
        """
        data = await self._request("GET", "/v1/auth/me")
        return UserInfo(**data)

    # Compliance check endpoints

    async def check_file(
        self,
        file_path: str | Path,
        rules: list[str] | None = None,
    ) -> ComplianceCheck:
        """Run a compliance check on a file.

        Args:
            file_path: Path to the file to check.
            rules: Optional list of rule IDs to check against.

        Returns:
            ComplianceCheck with the results.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise PretorianClientError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()

        client = await self._get_client()

        files = {"file": (file_path.name, content)}
        data: dict[str, Any] = {}
        if rules:
            data["rules"] = rules

        response = await client.post(
            "/v1/compliance/check",
            files=files,
            data=data,
        )

        if not response.is_success:
            self._handle_error(response)

        return ComplianceCheck(**response.json())

    async def check_content(
        self,
        content: str,
        filename: str = "document.txt",
        rules: list[str] | None = None,
    ) -> ComplianceCheck:
        """Run a compliance check on content.

        Args:
            content: The content to check.
            filename: Name to associate with the content.
            rules: Optional list of rule IDs to check against.

        Returns:
            ComplianceCheck with the results.
        """
        client = await self._get_client()

        files = {"file": (filename, content.encode())}
        data: dict[str, Any] = {}
        if rules:
            data["rules"] = rules

        response = await client.post(
            "/v1/compliance/check",
            files=files,
            data=data,
        )

        if not response.is_success:
            self._handle_error(response)

        return ComplianceCheck(**response.json())

    async def get_check(self, check_id: str) -> ComplianceCheck:
        """Get a compliance check by ID.

        Args:
            check_id: The ID of the check.

        Returns:
            ComplianceCheck with the results.
        """
        data = await self._request("GET", f"/v1/compliance/checks/{check_id}")
        return ComplianceCheck(**data)

    # Report endpoints

    async def list_reports(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReportListItem]:
        """List compliance reports.

        Args:
            limit: Maximum number of reports to return.
            offset: Number of reports to skip.

        Returns:
            List of report summaries.
        """
        data = await self._request(
            "GET",
            "/v1/reports",
            params={"limit": limit, "offset": offset},
        )
        return [ReportListItem(**item) for item in data.get("reports", [])]

    async def get_report(self, report_id: str) -> ComplianceReport:
        """Get a compliance report by ID.

        Args:
            report_id: The ID of the report.

        Returns:
            The full compliance report.
        """
        data = await self._request("GET", f"/v1/reports/{report_id}")
        return ComplianceReport(**data)

    async def create_report(
        self,
        name: str,
        file_paths: list[str | Path],
    ) -> ComplianceReport:
        """Create a new compliance report from multiple files.

        Args:
            name: Name for the report.
            file_paths: List of file paths to include.

        Returns:
            The created report.
        """
        client = await self._get_client()

        files = []
        for path in file_paths:
            path = Path(path)
            if not path.exists():
                raise PretorianClientError(f"File not found: {path}")
            with open(path, "rb") as f:
                files.append(("files", (path.name, f.read())))

        response = await client.post(
            "/v1/reports",
            files=files,
            data={"name": name},
        )

        if not response.is_success:
            self._handle_error(response)

        return ComplianceReport(**response.json())
