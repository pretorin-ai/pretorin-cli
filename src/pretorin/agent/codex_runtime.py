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

# SHA256 checksums per platform — verified on download.
# Maintainer must update these when bumping CODEX_VERSION.
CODEX_CHECKSUMS: dict[str, str] = {
    "darwin-arm64": "",
    "darwin-x64": "",
    "linux-x64": "",
}

CODEX_DOWNLOAD_URL = (
    "https://github.com/openai/codex/releases/download/{version}/"
    "codex-{platform}.tar.gz"
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

        lines = [
            f'model_provider = "{provider_name}"',
            'web_search = "disabled"',
            "",
            f"[model_providers.{provider_name}]",
            f'name = "{provider_name}"',
            f'base_url = "{base_url}"',
            f'wire_api = "{wire_api}"',
            f'env_key = "{env_key}"',
            "",
            "[mcp_servers.pretorin]",
            'command = "pretorin"',
            'args = ["mcp-serve"]',
        ]

        # Merge user MCP servers from ~/.pretorin/mcp.json if present
        extra_mcp = self._load_user_mcp_servers()
        for name, server in extra_mcp.items():
            lines.append("")
            lines.append(f"[mcp_servers.{name}]")
            if server.get("command"):
                lines.append(f'command = "{server["command"]}"')
            if server.get("args"):
                args_str = ", ".join(f'"{a}"' for a in server["args"])
                lines.append(f"args = [{args_str}]")
            if server.get("url"):
                lines.append(f'url = "{server["url"]}"')

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
        url = CODEX_DOWNLOAD_URL.format(version=self.version, platform=plat)
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
