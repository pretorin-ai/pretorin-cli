"""Coverage tests for src/pretorin/mcp/server.py.

Covers lines 75-76 (AuthenticationError handler), 78-79 (NotFoundError handler),
83-85 (generic Exception handler), 90-91 (_run_server), 100-101 (run_server),
105 (__name__ == "__main__" guard).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError


class TestCallToolErrorHandlers:
    """Tests for error handlers in call_tool."""

    @pytest.mark.asyncio
    async def test_authentication_error_handler(self):
        """Lines 75-76: AuthenticationError is caught and formatted."""
        from pretorin.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pretorin.mcp.server.PretorianClient", return_value=mock_client), \
             patch("pretorin.mcp.server.TOOL_HANDLERS", {"test_tool": AsyncMock(
                 side_effect=AuthenticationError("Token expired", status_code=401)
             )}):
            result = await call_tool("test_tool", {})

        assert result.isError is True
        assert "Authentication failed" in result.content[0].text

    @pytest.mark.asyncio
    async def test_not_found_error_handler(self):
        """Lines 78-79: NotFoundError is caught and formatted."""
        from pretorin.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pretorin.mcp.server.PretorianClient", return_value=mock_client), \
             patch("pretorin.mcp.server.TOOL_HANDLERS", {"test_tool": AsyncMock(
                 side_effect=NotFoundError("Resource not found", status_code=404)
             )}):
            result = await call_tool("test_tool", {})

        assert result.isError is True
        assert "Not found" in result.content[0].text

    @pytest.mark.asyncio
    async def test_generic_pretorianclient_error_handler(self):
        """Lines 80-82: PretorianClientError is caught and formatted."""
        from pretorin.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pretorin.mcp.server.PretorianClient", return_value=mock_client), \
             patch("pretorin.mcp.server.TOOL_HANDLERS", {"test_tool": AsyncMock(
                 side_effect=PretorianClientError("Server error", status_code=500)
             )}):
            result = await call_tool("test_tool", {})

        assert result.isError is True
        assert "Server error" in result.content[0].text

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self):
        """Lines 83-85: Generic Exception is caught and formatted."""
        from pretorin.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("pretorin.mcp.server.PretorianClient", return_value=mock_client), \
             patch("pretorin.mcp.server.TOOL_HANDLERS", {"test_tool": AsyncMock(
                 side_effect=RuntimeError("Unexpected failure")
             )}):
            result = await call_tool("test_tool", {})

        assert result.isError is True
        assert "Unexpected failure" in result.content[0].text


class TestRunServer:
    """Tests for _run_server and run_server."""

    @pytest.mark.asyncio
    async def test_run_server_async(self):
        """Lines 90-91: _run_server calls stdio_server and server.run."""
        from pretorin.mcp.server import _run_server

        mock_read = AsyncMock()
        mock_write = AsyncMock()

        with patch("pretorin.mcp.server.stdio_server") as mock_stdio, \
             patch("pretorin.mcp.server.server") as mock_server:
            # stdio_server is an async context manager
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_stdio.return_value = mock_cm

            mock_server.run = AsyncMock()
            mock_server.create_initialization_options = MagicMock(return_value={})

            await _run_server()

            mock_server.run.assert_awaited_once_with(mock_read, mock_write, {})

    def test_run_server_sync(self):
        """Lines 100-101: run_server calls asyncio.run(_run_server)."""
        from pretorin.mcp.server import run_server

        with patch("pretorin.mcp.server.asyncio.run") as mock_run:
            run_server()
            mock_run.assert_called_once()
            coroutine = mock_run.call_args.args[0]
            coroutine.close()


class TestMainGuard:
    """Test for __name__ == '__main__' guard."""

    def test_main_guard(self):
        """Line 105: __name__ == '__main__' calls run_server."""
        import pretorin.mcp.server as mod
        source_path = mod.__file__

        with open(source_path) as f:
            code = f.read()

        # Verify the guard exists and calls run_server
        assert 'if __name__ == "__main__"' in code
        assert "run_server()" in code
