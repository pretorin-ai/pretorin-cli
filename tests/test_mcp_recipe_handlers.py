"""Tests for MCP recipe-lifecycle handlers + write-tool stamping integration.

Covers WS2 Phase B's MCP surface:

- ``pretorin_start_recipe`` happy path: validates inputs, opens a context,
  returns context_id + body.
- Error cases: missing fields, unknown recipe id, version mismatch, nesting.
- ``pretorin_end_recipe`` happy path returns the RecipeResult; status
  validation; expired-context error.
- Write-tool stamping integration: ``handle_create_evidence`` /
  ``handle_create_evidence_batch`` accept ``recipe_context_id`` and stamp
  ``producer_kind="recipe"`` automatically.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.mcp.handlers.evidence import (
    handle_create_evidence,
    handle_create_evidence_batch,
)
from pretorin.mcp.handlers.recipe import (
    handle_end_recipe,
    handle_get_recipe,
    handle_list_recipes,
    handle_run_recipe_script,
    handle_start_recipe,
)
from pretorin.recipes import loader as loader_module
from pretorin.recipes.context import get_default_store, reset_default_store
from pretorin.recipes.loader import clear_cache
from pretorin.recipes.registry import script_tool_name

_FIXTURES = Path(__file__).parent / "recipes" / "fixtures" / "valid"


@pytest.fixture(autouse=True)
def _isolate_state() -> None:
    clear_cache()
    reset_default_store()
    yield
    clear_cache()
    reset_default_store()


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: builtin)
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: tmp_path / "no-user-dir")
    return {"builtin": builtin}


def _drop(source_dir: Path, fixture_name: str) -> None:
    shutil.copytree(_FIXTURES / fixture_name, source_dir / fixture_name)


def _extract_payload(response: Any) -> dict[str, Any]:
    """Pull the JSON dict from an MCP handler response.

    Successful handlers return ``list[TextContent]``; error handlers
    (``format_error``) return ``CallToolResult(content=[TextContent], isError=True)``
    per MCP convention. Handle both shapes so test assertions can be uniform.
    """
    if isinstance(response, list):
        text = response[0].text
    else:
        # CallToolResult — content is a list of TextContent.
        text = response.content[0].text
    # Errors come back as plain "Error: ..." strings; wrap them in a dict so
    # the rest of the test code can introspect uniformly.
    if not text.strip().startswith("{") and not text.strip().startswith("["):
        return {"error": text}
    return json.loads(text)


# =============================================================================
# pretorin_start_recipe — happy path
# =============================================================================


@pytest.mark.asyncio
async def test_start_recipe_happy_path(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    payload = _extract_payload(response)
    assert "context_id" in payload
    assert payload["recipe_id"] == "example-recipe"
    assert payload["recipe_version"] == "0.1.0"
    assert payload["tier"] == "official"
    # Body is the recipe.md body the calling agent reads.
    assert "Example Recipe Body" in payload["body"]


@pytest.mark.asyncio
async def test_start_recipe_stores_params_and_selection(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={
            "recipe_id": "example-recipe",
            "recipe_version": "0.1.0",
            "params": {"target": "rhel-9"},
            "selection": {"selected_recipe": "example-recipe", "confidence": "high"},
        },
    )
    payload = _extract_payload(response)
    ctx = get_default_store().get(payload["context_id"])
    assert ctx.params == {"target": "rhel-9"}
    assert ctx.selection == {"selected_recipe": "example-recipe", "confidence": "high"}


# =============================================================================
# pretorin_start_recipe — error cases
# =============================================================================


@pytest.mark.asyncio
async def test_start_recipe_missing_fields() -> None:
    response = await handle_start_recipe(client=MagicMock(), arguments={"recipe_id": "x"})
    payload = _extract_payload(response)
    assert "error" in payload or "Missing" in str(payload)


@pytest.mark.asyncio
async def test_start_recipe_unknown_id(fake_dirs: dict[str, Path]) -> None:
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "no-such-recipe", "recipe_version": "0.1.0"},
    )
    payload = _extract_payload(response)
    assert "no-such-recipe" in str(payload).lower() or "no recipe found" in str(payload).lower()


@pytest.mark.asyncio
async def test_start_recipe_version_mismatch(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "9.9.9"},
    )
    payload = _extract_payload(response)
    assert "version" in str(payload).lower()


@pytest.mark.asyncio
async def test_start_recipe_nesting_forbidden(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["builtin"], "another-recipe")

    await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    # Second start without ending the first → error.
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "another-recipe", "recipe_version": "1.2.3"},
    )
    payload = _extract_payload(response)
    assert "still active" in str(payload).lower() or "already" in str(payload).lower()


@pytest.mark.asyncio
async def test_start_recipe_invalid_params_type(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    response = await handle_start_recipe(
        client=MagicMock(),
        arguments={
            "recipe_id": "example-recipe",
            "recipe_version": "0.1.0",
            "params": "not-a-dict",
        },
    )
    payload = _extract_payload(response)
    assert "params" in str(payload).lower()


# =============================================================================
# pretorin_end_recipe
# =============================================================================


@pytest.mark.asyncio
async def test_end_recipe_happy_path(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    start = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    context_id = _extract_payload(start)["context_id"]
    end = await handle_end_recipe(client=MagicMock(), arguments={"context_id": context_id})
    payload = _extract_payload(end)
    assert payload["status"] == "pass"
    assert payload["recipe_id"] == "example-recipe"
    assert payload["evidence_count"] == 0
    assert payload["narrative_count"] == 0
    assert payload["errors"] == []


@pytest.mark.asyncio
async def test_end_recipe_with_status(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    start = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    context_id = _extract_payload(start)["context_id"]
    end = await handle_end_recipe(
        client=MagicMock(),
        arguments={"context_id": context_id, "status": "fail"},
    )
    assert _extract_payload(end)["status"] == "fail"


@pytest.mark.asyncio
async def test_end_recipe_invalid_status() -> None:
    response = await handle_end_recipe(
        client=MagicMock(),
        arguments={"context_id": "x", "status": "bogus"},
    )
    payload = _extract_payload(response)
    assert "status" in str(payload).lower()


@pytest.mark.asyncio
async def test_end_recipe_unknown_context_id() -> None:
    response = await handle_end_recipe(
        client=MagicMock(),
        arguments={"context_id": "not-a-real-id"},
    )
    payload = _extract_payload(response)
    assert "expired" in str(payload).lower() or "unknown" in str(payload).lower()


# =============================================================================
# Write-tool stamping integration
# =============================================================================


@pytest.fixture
def mock_client() -> AsyncMock:
    """A mock PretorianClient that returns reasonable defaults for write paths."""
    client = AsyncMock()
    client.list_evidence = AsyncMock(return_value=[])
    client.create_evidence = AsyncMock(return_value={"id": "ev-123"})
    client.create_evidence_batch = AsyncMock(
        return_value=MagicMock(model_dump=lambda: {"results": [{"index": 0, "status": "ok"}]})
    )
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})
    client.get_control = AsyncMock(return_value=MagicMock())
    return client


@pytest.fixture
def mock_resolve_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the real scope resolver in MCP write handlers."""

    async def _fake_scope(
        client: Any, arguments: Any, *, control_required: bool = False, enforce_active_context: bool = False
    ) -> tuple[str, str, str | None]:
        return ("system-1", "framework-1", "AC-2")

    monkeypatch.setattr("pretorin.mcp.handlers.evidence.resolve_execution_scope", _fake_scope)


@pytest.mark.asyncio
async def test_create_evidence_with_recipe_context_stamps_recipe(
    fake_dirs: dict[str, Path], mock_client: AsyncMock, mock_resolve_scope: None
) -> None:
    """Active recipe context → producer_kind='recipe' on the EvidenceCreate payload."""
    _drop(fake_dirs["builtin"], "example-recipe")
    start = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    context_id = _extract_payload(start)["context_id"]

    await handle_create_evidence(
        client=mock_client,
        arguments={
            "name": "test ev",
            "description": "This is a test evidence record.\n\n- Item one\n- Item two\n",
            "evidence_type": "code_snippet",
            "recipe_context_id": context_id,
        },
    )

    # Inspect the payload that was passed to the kernel via upsert_evidence.
    # The mock client's create_evidence was called with (system_id, EvidenceCreate(...)).
    # upsert_evidence calls client.create_evidence after constructing the payload.
    assert mock_client.create_evidence.await_count == 1
    _system_id, payload = mock_client.create_evidence.await_args.args
    assert payload.audit_metadata is not None
    assert payload.audit_metadata.producer_kind == "recipe"
    assert payload.audit_metadata.producer_id == "example-recipe"
    assert payload.audit_metadata.producer_version == "0.1.0"


@pytest.mark.asyncio
async def test_create_evidence_without_context_stamps_agent(
    fake_dirs: dict[str, Path], mock_client: AsyncMock, mock_resolve_scope: None
) -> None:
    """No recipe_context_id → producer_kind='agent' (the default for MCP write path)."""
    await handle_create_evidence(
        client=mock_client,
        arguments={
            "name": "test ev",
            "description": "This is a test evidence record.\n\n- Item one\n- Item two\n",
            "evidence_type": "code_snippet",
        },
    )
    assert mock_client.create_evidence.await_count == 1
    _system_id, payload = mock_client.create_evidence.await_args.args
    assert payload.audit_metadata is not None
    assert payload.audit_metadata.producer_kind == "agent"
    assert payload.audit_metadata.producer_id == "mcp-agent"


@pytest.mark.asyncio
async def test_create_evidence_invalid_recipe_context_returns_error(
    mock_client: AsyncMock, mock_resolve_scope: None
) -> None:
    """A bogus recipe_context_id surfaces a clear error rather than silently freelancing."""
    response = await handle_create_evidence(
        client=mock_client,
        arguments={
            "name": "test ev",
            "description": "This is a test evidence record.\n\n- Item one\n- Item two\n",
            "evidence_type": "code_snippet",
            "recipe_context_id": "not-a-real-id",
        },
    )
    payload = _extract_payload(response)
    assert "expired" in str(payload).lower() or "unknown" in str(payload).lower()
    # And the write was NOT attempted.
    assert mock_client.create_evidence.await_count == 0


@pytest.mark.asyncio
async def test_create_evidence_with_context_bumps_evidence_count(
    fake_dirs: dict[str, Path], mock_client: AsyncMock, mock_resolve_scope: None
) -> None:
    """The context tally updates so end_recipe reports it correctly."""
    _drop(fake_dirs["builtin"], "example-recipe")
    start = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    context_id = _extract_payload(start)["context_id"]

    for _ in range(3):
        await handle_create_evidence(
            client=mock_client,
            arguments={
                "name": "test ev",
                "description": "x",
                "evidence_type": "code_snippet",
                "recipe_context_id": context_id,
            },
        )

    end = await handle_end_recipe(client=MagicMock(), arguments={"context_id": context_id})
    payload = _extract_payload(end)
    assert payload["evidence_count"] == 3


@pytest.mark.asyncio
async def test_create_evidence_batch_with_recipe_context(
    fake_dirs: dict[str, Path], mock_client: AsyncMock, mock_resolve_scope: None
) -> None:
    """Each batch item inherits the recipe context's stamping."""
    _drop(fake_dirs["builtin"], "example-recipe")
    start = await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    context_id = _extract_payload(start)["context_id"]

    await handle_create_evidence_batch(
        client=mock_client,
        arguments={
            "items": [
                {
                    "name": "a",
                    "description": "Batch item A.\n\n- one\n- two",
                    "control_id": "AC-2",
                    "evidence_type": "code_snippet",
                },
                {
                    "name": "b",
                    "description": "Batch item B.\n\n- one\n- two",
                    "control_id": "AC-2",
                    "evidence_type": "code_snippet",
                },
            ],
            "recipe_context_id": context_id,
        },
    )

    assert mock_client.create_evidence_batch.await_count == 1
    _system_id, _framework_id, items = mock_client.create_evidence_batch.await_args.args
    for item in items:
        assert item.audit_metadata is not None
        assert item.audit_metadata.producer_kind == "recipe"
        assert item.audit_metadata.producer_id == "example-recipe"


# =============================================================================
# Phase C: pretorin_list_recipes / pretorin_get_recipe
# =============================================================================


@pytest.mark.asyncio
async def test_list_recipes_empty(fake_dirs: dict[str, Path]) -> None:
    response = await handle_list_recipes(client=MagicMock(), arguments={})
    payload = _extract_payload(response)
    assert payload["total"] == 0
    assert payload["recipes"] == []


@pytest.mark.asyncio
async def test_list_recipes_returns_summary(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["builtin"], "another-recipe")
    response = await handle_list_recipes(client=MagicMock(), arguments={})
    payload = _extract_payload(response)
    assert payload["total"] == 2
    ids = {r["id"] for r in payload["recipes"]}
    assert ids == {"example-recipe", "another-recipe"}
    # Body intentionally NOT included in list — that's get_recipe's job.
    for recipe in payload["recipes"]:
        assert "body" not in recipe
        # Summary fields are present.
        for field_name in ["id", "name", "tier", "description", "use_when", "produces"]:
            assert field_name in recipe


@pytest.mark.asyncio
async def test_list_recipes_filter_by_tier(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")  # → official
    response = await handle_list_recipes(
        client=MagicMock(),
        arguments={"tier": "community"},
    )
    payload = _extract_payload(response)
    assert payload["total"] == 0  # builtin → official, filtered out


@pytest.mark.asyncio
async def test_list_recipes_filter_by_produces(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")  # produces evidence
    _drop(fake_dirs["builtin"], "another-recipe")  # produces narrative
    response = await handle_list_recipes(
        client=MagicMock(),
        arguments={"produces": "narrative"},
    )
    payload = _extract_payload(response)
    assert payload["total"] == 1
    assert payload["recipes"][0]["id"] == "another-recipe"


@pytest.mark.asyncio
async def test_get_recipe_unknown_id(fake_dirs: dict[str, Path]) -> None:
    response = await handle_get_recipe(client=MagicMock(), arguments={"recipe_id": "no-such-recipe"})
    payload = _extract_payload(response)
    assert "no recipe found" in str(payload).lower()


@pytest.mark.asyncio
async def test_get_recipe_returns_full_body_and_manifest(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    response = await handle_get_recipe(client=MagicMock(), arguments={"recipe_id": "example-recipe"})
    payload = _extract_payload(response)
    assert payload["id"] == "example-recipe"
    assert "body" in payload
    assert "Example Recipe Body" in payload["body"]
    assert payload["manifest"]["name"] == "Example Recipe"
    assert payload["source"] == "builtin"


# =============================================================================
# Phase C: handle_run_recipe_script (per-recipe-script dispatcher)
# =============================================================================


@pytest.mark.asyncio
async def test_run_recipe_script_requires_active_context(fake_dirs: dict[str, Path]) -> None:
    """Script-tool calls outside an active recipe context are rejected."""
    _drop(fake_dirs["builtin"], "example-recipe")
    # Drop a real script file so the manifest's reference resolves.
    script_file = fake_dirs["builtin"] / "example-recipe" / "scripts" / "example.py"
    script_file.parent.mkdir(exist_ok=True)
    script_file.write_text('"""."""\nasync def run(ctx, **params):\n    return {"ok": True}\n')

    tool_name = script_tool_name("example-recipe", "example_tool")
    response = await handle_run_recipe_script(
        client=MagicMock(),
        arguments={},
        tool_name=tool_name,
    )
    payload = _extract_payload(response)
    assert "active recipe execution context" in str(payload).lower()


@pytest.mark.asyncio
async def test_run_recipe_script_unknown_tool_name(fake_dirs: dict[str, Path]) -> None:
    response = await handle_run_recipe_script(
        client=MagicMock(),
        arguments={},
        tool_name="pretorin_recipe_unknown__nope",
    )
    payload = _extract_payload(response)
    assert "no recipe script tool" in str(payload).lower()


@pytest.mark.asyncio
async def test_run_recipe_script_wrong_recipe_context(fake_dirs: dict[str, Path]) -> None:
    """Active context for recipe A; calling recipe B's script is rejected."""
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["builtin"], "another-recipe")
    script_file = fake_dirs["builtin"] / "example-recipe" / "scripts" / "example.py"
    script_file.parent.mkdir(exist_ok=True)
    script_file.write_text('"""."""\nasync def run(ctx, **params):\n    return {}\n')

    # Start the another-recipe context (no scripts).
    await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "another-recipe", "recipe_version": "1.2.3"},
    )
    # Now try to call example-recipe's script.
    tool_name = script_tool_name("example-recipe", "example_tool")
    response = await handle_run_recipe_script(
        client=MagicMock(),
        arguments={},
        tool_name=tool_name,
    )
    payload = _extract_payload(response)
    assert "active recipe context is for" in str(payload).lower()


@pytest.mark.asyncio
async def test_run_recipe_script_happy_path(fake_dirs: dict[str, Path]) -> None:
    """With an active matching context, the script's run() executes and returns its dict."""
    _drop(fake_dirs["builtin"], "example-recipe")
    script_file = fake_dirs["builtin"] / "example-recipe" / "scripts" / "example.py"
    script_file.parent.mkdir(exist_ok=True)
    script_file.write_text(
        '"""."""\n'
        "async def run(ctx, **params):\n"
        '    return {"ok": True, "input": params.get("input"), "ctx_recipe": ctx.recipe_id}\n'
    )

    await handle_start_recipe(
        client=MagicMock(),
        arguments={"recipe_id": "example-recipe", "recipe_version": "0.1.0"},
    )
    tool_name = script_tool_name("example-recipe", "example_tool")
    response = await handle_run_recipe_script(
        client=MagicMock(),
        arguments={"input": "hello"},
        tool_name=tool_name,
    )
    payload = _extract_payload(response)
    assert payload["ok"] is True
    assert payload["input"] == "hello"
    assert payload["ctx_recipe"] == "example-recipe"


# =============================================================================
# Phase C: list_tools includes per-recipe-script tools dynamically
# =============================================================================


@pytest.mark.asyncio
async def test_list_tools_includes_dynamic_script_tools(fake_dirs: dict[str, Path]) -> None:
    """Loaded recipes' scripts show up in the MCP tool list."""
    from pretorin.mcp.tools import list_tools

    _drop(fake_dirs["builtin"], "example-recipe")
    tools = await list_tools()
    tool_names = {t.name for t in tools}
    expected = script_tool_name("example-recipe", "example_tool")
    assert expected in tool_names

    # Schema is built from ScriptDecl.params — should include "input".
    matching = next(t for t in tools if t.name == expected)
    assert "input" in matching.inputSchema["properties"]
