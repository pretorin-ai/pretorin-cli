"""Codex binary lifecycle management with full isolation.

Downloads, verifies, and manages a pinned Codex binary under ~/.pretorin/bin/
with configuration isolated to ~/.pretorin/codex/ (never touches ~/.codex/).
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

CODEX_VERSION = "rust-v0.88.0-alpha.3"

# Mapping from our simplified platform keys to Rust target triples used in release assets.
_PLATFORM_TO_TARGET: dict[str, str] = {
    "darwin-arm64": "aarch64-apple-darwin",
    "darwin-x64": "x86_64-apple-darwin",
    "linux-x64": "x86_64-unknown-linux-gnu",
}

# SHA256 checksums per platform — verified on download.
# Maintainer must update these when bumping CODEX_VERSION.
CODEX_CHECKSUMS: dict[str, str] = {
    "darwin-arm64": "a20463a19ed5dd7fe01cdd14cbdf11e7a1b23296135df61aba65944dc0ac5367",
    "darwin-x64": "ea5a1343cd1b7216ccf6085257217ef1819f54c237cb60e33a9f000f4456405d",
    "linux-x64": "e3dd97f06ad09f7893e73d7ea091bdc5045ef7bd7ba306140d13a14d512cdc5f",
}

CODEX_DOWNLOAD_URL = (
    "https://github.com/openai/codex/releases/download/{version}/"
    "codex-{target}.tar.gz"
)


def _detect_platform() -> str:
    """Return the platform key for binary downloads.

    Returns one of: 'darwin-arm64', 'darwin-x64', 'linux-x64'.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        return "darwin-arm64" if machine == "arm64" else "darwin-x64"
    elif system == "linux":
        return "linux-x64"
    raise RuntimeError(f"Unsupported platform: {system}/{machine}")


class CodexRuntime:
    """Manages the pinned Codex binary."""

    def __init__(self, version: str = CODEX_VERSION) -> None:
        self.version = version
        self.bin_dir = Path.home() / ".pretorin" / "bin"
        self.codex_home = Path.home() / ".pretorin" / "codex"

    @property
    def binary_path(self) -> Path:
        """Path to the pinned binary."""
        return self.bin_dir / f"codex-{self.version}"

    @property
    def is_installed(self) -> bool:
        """Check if the pinned version is available and executable."""
        p = self.binary_path
        return p.exists() and bool(p.stat().st_mode & 0o111)

    def ensure_installed(self) -> Path:
        """Download and verify if not present. Returns binary path."""
        if self.is_installed:
            return self.binary_path
        self._download()
        self._verify_checksum()
        self._make_executable()
        return self.binary_path

    def build_env(self, api_key: str, base_url: str, **extra: str) -> dict[str, str]:
        """Build an isolated environment for the Codex process.

        Sets CODEX_HOME to ~/.pretorin/codex/ so the binary never reads
        ~/.codex/config.toml.
        """
        env: dict[str, str] = {
            "CODEX_HOME": str(self.codex_home),
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
        }
        env.update(extra)
        return env

    @staticmethod
    def _toml_escape(value: str) -> str:
        """Escape a string value for safe TOML embedding."""
        # Replace backslashes first, then quotes and control characters
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        value = value.replace("\t", "\\t")
        return value

    @staticmethod
    def _toml_bare_key(key: str) -> str:
        """Validate a string is safe for use as a TOML bare key."""
        import re

        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise ValueError(f"Invalid TOML key: {key!r}")
        return key

    def write_config(
        self,
        model: str,
        provider_name: str,
        base_url: str,
        env_key: str,
        wire_api: str = "responses",
    ) -> Path:
        """Write an isolated config.toml under CODEX_HOME.

        This config is Pretorin-managed and never touches ~/.codex/.
        """
        self.codex_home.mkdir(parents=True, exist_ok=True)
        config_path = self.codex_home / "config.toml"

        safe_provider = self._toml_bare_key(provider_name)
        esc = self._toml_escape

        lines = [
            f'model_provider = "{esc(safe_provider)}"',
            'web_search = "disabled"',
            "",
            f"[model_providers.{safe_provider}]",
            f'name = "{esc(safe_provider)}"',
            f'base_url = "{esc(base_url)}"',
            f'wire_api = "{esc(wire_api)}"',
            f'env_key = "{esc(env_key)}"',
            "",
            "[mcp_servers.pretorin]",
            'command = "pretorin"',
            'args = ["mcp-serve"]',
        ]

        # Merge user MCP servers from ~/.pretorin/mcp.json if present
        extra_mcp = self._load_user_mcp_servers()
        for name, server in extra_mcp.items():
            safe_name = self._toml_bare_key(name)
            lines.append("")
            lines.append(f"[mcp_servers.{safe_name}]")
            if server.get("command"):
                lines.append(f'command = "{esc(str(server["command"]))}"')
            if server.get("args"):
                args_str = ", ".join(f'"{esc(str(a))}"' for a in server["args"])
                lines.append(f"args = [{args_str}]")
            if server.get("url"):
                lines.append(f'url = "{esc(str(server["url"]))}"')

        config_path.write_text("\n".join(lines) + "\n")
        return config_path

    def cleanup_old_versions(self) -> list[Path]:
        """Remove binaries that don't match the current pinned version."""
        removed: list[Path] = []
        if not self.bin_dir.exists():
            return removed
        current_name = self.binary_path.name
        for entry in self.bin_dir.iterdir():
            if entry.name.startswith("codex-") and entry.name != current_name:
                entry.unlink()
                removed.append(entry)
                logger.info("Removed old Codex binary: %s", entry)
        return removed

    def _download(self) -> None:
        """Download the Codex binary tarball for the current platform."""
        plat = _detect_platform()
        target = _PLATFORM_TO_TARGET.get(plat, plat)
        url = CODEX_DOWNLOAD_URL.format(version=self.version, target=target)
        logger.info("Downloading Codex %s for %s from %s", self.version, plat, url)

        self.bin_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
                response.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

            # Store the tarball path for checksum verification before extraction
            self._tarball_path = tmp_path

        except httpx.HTTPError as e:
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to download Codex binary: {e}") from e

    def _verify_checksum(self) -> None:
        """Verify SHA256 checksum of the downloaded tarball."""
        plat = _detect_platform()
        expected = CODEX_CHECKSUMS.get(plat, "")

        if not expected:
            logger.warning("No checksum configured for %s — skipping verification", plat)
            self._extract_tarball()
            return

        sha256 = hashlib.sha256()
        with open(self._tarball_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        actual = sha256.hexdigest()
        if actual != expected:
            self._tarball_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Checksum mismatch for {plat}:\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual}"
            )

        self._extract_tarball()

    def _extract_tarball(self) -> None:
        """Extract the codex binary from the tarball."""
        try:
            with tarfile.open(self._tarball_path, "r:gz") as tar:
                # Find the codex binary inside the archive
                members = tar.getnames()
                codex_member = None
                for name in members:
                    basename = Path(name).name
                    if basename == "codex" or basename.startswith("codex-"):
                        codex_member = name
                        break

                if codex_member is None:
                    # If no specific codex binary found, extract all and look for it
                    with tempfile.TemporaryDirectory() as extract_dir:
                        tar.extractall(extract_dir)
                        # Find the binary
                        for root, _dirs, files in os.walk(extract_dir):
                            for fname in files:
                                if fname in ("codex", "codex-cli"):
                                    src = Path(root) / fname
                                    shutil.copy2(src, self.binary_path)
                                    return
                    raise RuntimeError("Could not find codex binary in tarball")
                else:
                    extracted = tar.extractfile(codex_member)
                    if extracted is None:
                        raise RuntimeError(f"Could not extract {codex_member} from tarball")
                    with open(self.binary_path, "wb") as out:
                        shutil.copyfileobj(extracted, out)
        finally:
            self._tarball_path.unlink(missing_ok=True)

    def _make_executable(self) -> None:
        """Set the binary as executable."""
        self.binary_path.chmod(self.binary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _load_user_mcp_servers(self) -> dict[str, dict[str, object]]:
        """Load user-configured MCP servers from ~/.pretorin/mcp.json."""
        import json

        mcp_path = Path.home() / ".pretorin" / "mcp.json"
        if not mcp_path.exists():
            return {}
        try:
            data = json.loads(mcp_path.read_text())
            servers: dict[str, dict[str, object]] = {}
            for name, config in data.get("servers", {}).items():
                if name == "pretorin":
                    continue  # Already injected
                servers[name] = config
            return servers
        except (json.JSONDecodeError, OSError):
            return {}
