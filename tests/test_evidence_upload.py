"""Tests for evidence upload — CLI command and MCP handler."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.evidence import app
from pretorin.cli.output import set_json_mode


runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.client.api.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


class TestUploadCLI:
    def test_upload_success(self, tmp_path: Path) -> None:
        f = tmp_path / "screenshot.png"
        f.write_bytes(b"\x89PNG" + b"\x00" * 100)  # valid PNG magic bytes

        client = AsyncMock()
        client.is_configured = True
        client.upload_evidence = AsyncMock(
            return_value={
                "evidence_id": "ev-123",
                "file_name": "screenshot.png",
                "file_size": 104,
                "checksum": "abc123",
                "evidence_type": "screenshot",
            }
        )
        client.get_system = AsyncMock(return_value=AsyncMock(name="Test System"))
        client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])

        with patch("pretorin.cli.context.resolve_execution_context", new=AsyncMock(return_value=("sys-1", "fedramp-moderate"))):
            result = _run_with_mock_client(
                [
                    "upload",
                    str(f),
                    "ac-02",
                    "fedramp-moderate",
                    "--name",
                    "MFA Screenshot",
                    "--type",
                    "screenshot",
                ],
                client,
            )
        assert result.exit_code == 0

    def test_upload_invalid_type(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("test")

        client = AsyncMock()
        client.is_configured = True

        result = _run_with_mock_client(
            [
                "upload",
                str(f),
                "ac-02",
                "fedramp-moderate",
                "--name",
                "Test",
                "--type",
                "INVALID_TYPE",
            ],
            client,
        )
        assert result.exit_code == 1


class TestUploadMCPHandler:
    @pytest.mark.anyio
    async def test_missing_required_fields(self) -> None:
        from pretorin.mcp.handlers.evidence import handle_upload_evidence

        client = AsyncMock()
        client.is_configured = True
        result = await handle_upload_evidence(client, {})
        # Should return error for missing file_path and name
        assert hasattr(result, "isError") and result.isError is True

    @pytest.mark.anyio
    async def test_success(self) -> None:
        from pretorin.mcp.handlers.evidence import handle_upload_evidence

        client = AsyncMock()
        client.is_configured = True
        client.upload_evidence = AsyncMock(
            return_value={"evidence_id": "ev-1", "checksum": "abc"}
        )

        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_upload_evidence(
                client,
                {
                    "file_path": "/tmp/test.pdf",
                    "name": "Test Evidence",
                    "evidence_type": "policy_document",
                },
            )
        assert not (hasattr(result, "isError") and result.isError)
        client.upload_evidence.assert_awaited_once()


class TestUploadClientValidation:
    """Test client-side file validation in api.py upload_evidence()."""

    @pytest.mark.anyio
    async def test_rejects_missing_file(self) -> None:
        from pretorin.client.api import PretorianClient, PretorianClientError

        client = PretorianClient.__new__(PretorianClient)
        with pytest.raises(PretorianClientError, match="File not found"):
            await client.upload_evidence(
                system_id="sys-1",
                file_path="/nonexistent/file.pdf",
                name="test",
            )

    @pytest.mark.anyio
    async def test_rejects_empty_file(self, tmp_path: Path) -> None:
        from pretorin.client.api import PretorianClient, PretorianClientError

        f = tmp_path / "empty.txt"
        f.write_text("")

        client = PretorianClient.__new__(PretorianClient)
        with pytest.raises(PretorianClientError, match="Empty files"):
            await client.upload_evidence(
                system_id="sys-1",
                file_path=str(f),
                name="test",
            )

    @pytest.mark.anyio
    async def test_rejects_blocked_extension(self, tmp_path: Path) -> None:
        from pretorin.client.api import PretorianClient, PretorianClientError

        f = tmp_path / "malware.exe"
        f.write_bytes(b"\x00" * 100)

        client = PretorianClient.__new__(PretorianClient)
        with pytest.raises(PretorianClientError, match="extension.*not allowed"):
            await client.upload_evidence(
                system_id="sys-1",
                file_path=str(f),
                name="test",
            )

    @pytest.mark.anyio
    async def test_rejects_oversized_file(self, tmp_path: Path) -> None:
        from pretorin.client.api import PretorianClient, PretorianClientError

        f = tmp_path / "huge.pdf"
        # Write just over 25MB
        f.write_bytes(b"\x00" * (25 * 1024 * 1024 + 1))

        client = PretorianClient.__new__(PretorianClient)
        with pytest.raises(PretorianClientError, match="25MB"):
            await client.upload_evidence(
                system_id="sys-1",
                file_path=str(f),
                name="test",
            )
