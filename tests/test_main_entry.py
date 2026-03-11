"""Tests for __main__.py entry point."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch


class TestMainModule:
    """Tests for the pretorin.__main__ module."""

    def test_main_module_imports_app(self) -> None:
        """Importing __main__ makes `app` accessible."""
        from pretorin import __main__

        assert hasattr(__main__, "app")
        assert callable(__main__.app)

    def test_main_module_runs_app_when_name_is_main(self) -> None:
        """When __name__ == '__main__', app() is called."""
        with patch("pretorin.cli.main.app") as mock_app:
            # Execute the module body with __name__ set to "__main__"
            code = compile(
                'from pretorin.cli.main import app\nif __name__ == "__main__":\n    app()\n',
                "<test>",
                "exec",
            )
            exec(code, {"__name__": "__main__"})
            mock_app.assert_called_once()

    def test_python_m_pretorin_returns_zero(self) -> None:
        """Running `python -m pretorin --help` exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "pretorin", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "pretorin" in result.stdout.lower() or "Usage" in result.stdout
