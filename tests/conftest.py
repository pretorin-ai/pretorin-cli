"""Shared test configuration and fixtures for Pretorin CLI tests."""

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires API key)"
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip integration tests unless explicitly requested."""
    # Check if we should run integration tests
    run_integration = (
        os.environ.get("PRETORIN_API_KEY")
        or config.getoption("-m", default="") == "integration"
        or "integration" in config.getoption("-k", default="")
    )

    if not run_integration:
        skip_integration = pytest.mark.skip(
            reason="Integration tests require PRETORIN_API_KEY or -m integration"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
