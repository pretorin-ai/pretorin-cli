"""MCP server configuration for the agent.

Loads MCP server configs from:
- `.pretorin-mcp.json` (project-level)
- `~/.pretorin/mcp.json` (global)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    transport: str  # "stdio" or "http"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None

    def validate(self) -> None:
        """Validate the config is complete for its transport type."""
        if self.transport == "stdio" and not self.command:
            raise ValueError(f"MCP server '{self.name}': stdio transport requires 'command'")
        if self.transport == "http" and not self.url:
            raise ValueError(f"MCP server '{self.name}': http transport requires 'url'")

    def to_sdk_server(self) -> Any:
        """Convert to an OpenAI Agents SDK MCP server instance.

        Returns:
            MCPServerStdio or MCPServerStreamableHttp instance.

        Raises:
            ImportError: If openai-agents is not installed.
        """
        try:
            from agents.mcp import MCPServerStdio, MCPServerStreamableHttp
        except ImportError:
            raise ImportError(
                "openai-agents is required for MCP server connections. "
                "Install with: pip install pretorin[agent]"
            )

        self.validate()

        if self.transport == "stdio":
            return MCPServerStdio(
                name=self.name,
                params={
                    "command": self.command,
                    "args": self.args,
                    "env": self.env if self.env else None,
                },
            )
        elif self.transport == "http":
            return MCPServerStreamableHttp(
                name=self.name,
                params={"url": self.url},
            )
        else:
            raise ValueError(f"Unknown transport: {self.transport}")


PROJECT_CONFIG_FILE = ".pretorin-mcp.json"
GLOBAL_CONFIG_FILE = Path.home() / ".pretorin" / "mcp.json"


class MCPConfigManager:
    """Manages MCP server configurations from project and global config files."""

    def __init__(self) -> None:
        self._servers: list[MCPServerConfig] = []
        self._load()

    def _load(self) -> None:
        """Load configs from project-level then global, project takes precedence."""
        seen_names: set[str] = set()

        # Project-level config
        project_path = Path.cwd() / PROJECT_CONFIG_FILE
        if project_path.exists():
            for server in self._parse_file(project_path):
                if server.name not in seen_names:
                    self._servers.append(server)
                    seen_names.add(server.name)

        # Global config
        if GLOBAL_CONFIG_FILE.exists():
            for server in self._parse_file(GLOBAL_CONFIG_FILE):
                if server.name not in seen_names:
                    self._servers.append(server)
                    seen_names.add(server.name)

    @staticmethod
    def _parse_file(path: Path) -> list[MCPServerConfig]:
        """Parse a JSON config file into MCPServerConfig objects."""
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        servers = data.get("servers", [])
        result = []
        for entry in servers:
            try:
                result.append(MCPServerConfig(
                    name=entry["name"],
                    transport=entry.get("transport", "stdio"),
                    command=entry.get("command"),
                    args=entry.get("args", []),
                    env=entry.get("env", {}),
                    url=entry.get("url"),
                ))
            except (KeyError, TypeError):
                continue
        return result

    @property
    def servers(self) -> list[MCPServerConfig]:
        """Return all configured MCP servers."""
        return list(self._servers)

    def to_sdk_servers(self) -> list[Any]:
        """Convert all configs to SDK server instances."""
        return [s.to_sdk_server() for s in self._servers]

    def add_server(self, config: MCPServerConfig, scope: str = "project") -> None:
        """Add a server configuration and persist it.

        Args:
            config: Server configuration to add.
            scope: "project" for .pretorin-mcp.json, "global" for ~/.pretorin/mcp.json.
        """
        # Remove existing with same name
        self._servers = [s for s in self._servers if s.name != config.name]
        self._servers.append(config)

        path = Path.cwd() / PROJECT_CONFIG_FILE if scope == "project" else GLOBAL_CONFIG_FILE
        self._save_to_file(path, config, remove=False)

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration by name.

        Returns:
            True if a server was removed.
        """
        original_count = len(self._servers)
        self._servers = [s for s in self._servers if s.name != name]

        if len(self._servers) < original_count:
            # Try to remove from both files
            for path in [Path.cwd() / PROJECT_CONFIG_FILE, GLOBAL_CONFIG_FILE]:
                if path.exists():
                    self._remove_from_file(path, name)
            return True
        return False

    @staticmethod
    def _save_to_file(path: Path, config: MCPServerConfig, remove: bool = False) -> None:
        """Save or update a server config in a JSON file."""
        data: dict[str, Any] = {"servers": []}
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {"servers": []}

        servers = data.get("servers", [])
        # Remove existing entry with same name
        servers = [s for s in servers if s.get("name") != config.name]

        if not remove:
            entry: dict[str, Any] = {
                "name": config.name,
                "transport": config.transport,
            }
            if config.command:
                entry["command"] = config.command
            if config.args:
                entry["args"] = config.args
            if config.env:
                entry["env"] = config.env
            if config.url:
                entry["url"] = config.url
            servers.append(entry)

        data["servers"] = servers
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _remove_from_file(path: Path, name: str) -> None:
        """Remove a server entry from a JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        servers = data.get("servers", [])
        data["servers"] = [s for s in servers if s.get("name") != name]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
