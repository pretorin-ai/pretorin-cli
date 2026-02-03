# Changelog

All notable changes to the Pretorin CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-02-03

### Added
- Initial public release
- CLI commands for browsing compliance frameworks
  - `pretorin frameworks list` - List all frameworks
  - `pretorin frameworks get` - Get framework details
  - `pretorin frameworks families` - List control families
  - `pretorin frameworks controls` - List controls
  - `pretorin frameworks control` - Get control details
  - `pretorin frameworks documents` - Get document requirements
- Authentication commands
  - `pretorin login` - Authenticate with API key
  - `pretorin logout` - Clear stored credentials
  - `pretorin whoami` - Show authentication status
- Configuration management
  - `pretorin config list` - List all configuration
  - `pretorin config get` - Get a config value
  - `pretorin config set` - Set a config value
  - `pretorin config path` - Show config file path
- MCP (Model Context Protocol) server for AI assistant integration
  - 7 tools for accessing compliance data
  - Resources for analysis guidance
  - Setup instructions for Claude Desktop, Claude Code, Cursor, Codex CLI, and Windsurf
- Self-update functionality via `pretorin update`
- Version checking with PyPI update notifications
- Rich terminal output with branded styling
- Rome-bot ASCII mascot with expressive animations
- Docker support with multi-stage Dockerfile
- Docker Compose configuration for containerized testing
- GitHub Actions CI/CD workflows for testing and PyPI publishing
- Integration test suite for CLI commands and MCP tools
- Comprehensive MCP documentation in `docs/MCP.md`

### Supported Frameworks
- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2/3
- FedRAMP (Low, Moderate, High)
- CMMC Level 1, 2, and 3
- Additional frameworks available on the platform

[Unreleased]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pretorin-ai/pretorin-cli/releases/tag/v0.1.0
