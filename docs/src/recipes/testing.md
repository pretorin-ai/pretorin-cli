# Testing Recipes

Recipes are real Python modules — test them like any other Python code. The
scaffolder drops a `tests/test_recipe.py` stub when you run
`pretorin recipe new <id>`; this page covers what to put in it.

## Three Layers Worth Testing

A recipe has three layers and each rewards a different test style:

1. **Pure helpers inside `scripts/`** — redaction, normalization, parsers.
   Plain unit tests with no fixtures. Fastest feedback loop; most coverage
   per line of test code.
2. **`run` against a fake `ctx`** — the script's main entry point. Mock
   `ctx.api_client` so you don't hit the network.
3. **End-to-end through the recipe runner** — load the recipe, call its
   script through the runner, assert the result. Slower but proves the
   manifest, the importlib-based dispatch, and the script all line up.

## Unit-Testing Helpers

If you've factored out helpers into `scripts/redact.py` or
`scripts/normalize.py`, import them directly:

```python
# tests/test_helpers.py
from scripts.redact import redact_aws_keys

def test_redact_aws_keys_replaces_full_key() -> None:
    text = "AKIAIOSFODNN7EXAMPLE"
    redacted = redact_aws_keys(text)
    assert "AKIA" not in redacted
    assert "[REDACTED:AWS_KEY]" in redacted
```

The recipe runner adds the `scripts/` directory to `sys.path`. In tests,
make sure your `pytest.ini` or `pyproject.toml` does the same:

```toml
[tool.pytest.ini_options]
pythonpath = ["scripts"]
```

## Testing `run` with a Fake `ctx`

The script's `run` function takes a `ctx` argument typed as
`Any` (loose intentionally — see [Script contract](./script-contract.md)).
A `MagicMock` with `AsyncMock` for the I/O methods is enough:

```python
# tests/test_run.py
from unittest.mock import AsyncMock, MagicMock
import pytest

from scripts.run_scan import run

@pytest.mark.asyncio
async def test_run_returns_summary_for_no_rules() -> None:
    ctx = MagicMock()
    ctx.system_id = "sys-1"
    ctx.api_client = MagicMock()
    ctx.api_client.get_test_manifest = AsyncMock(
        return_value={"applicable_stigs": []}
    )

    result = await run(ctx, stig_id="EMPTY_STIG")

    assert result["stig_id"] == "EMPTY_STIG"
    assert result["summary"]["total"] == 0
```

The four scanner recipe tests in pretorin-cli's test suite use exactly
this shape — patch `get_test_manifest`, call `run`, assert on the
returned summary.

## End-to-End Through the Runner

The strongest test exercises the full path: registry loads the manifest,
runner imports the script, script runs against a fake API client. This
is what `tests/recipes/test_code_evidence_capture.py` does for the
`code-evidence-capture` recipe and it's the regression-test pattern to
copy.

Sketch:

```python
import pytest
from pretorin.recipes import loader as loader_module
from pretorin.recipes.loader import clear_cache
from pretorin.recipes.registry import RecipeRegistry
from pretorin.recipes.runner import RecipeScriptContext, run_script
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    clear_cache()
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: tmp_path / "u")
    monkeypatch.setattr(loader_module, "_project_recipes_root", lambda start=None: None)

@pytest.mark.asyncio
async def test_my_recipe_end_to_end() -> None:
    registry = RecipeRegistry()
    entry = registry.get("my-recipe")
    assert entry is not None

    api_client = MagicMock()
    api_client.create_evidence = AsyncMock(return_value={"id": "ev-1"})
    ctx = RecipeScriptContext(
        system_id="sys-1",
        framework_id="nist-800-53-r5",
        api_client=api_client,
        logger=MagicMock(),
        recipe_id="my-recipe",
        recipe_version="0.1.0",
        recipe_context_id=None,
    )

    result = await run_script(
        recipe=entry.active,
        script_name="capture",
        ctx=ctx,
        params={"control_id": "ac-2"},
    )

    assert result["evidence_id"] == "ev-1"
```

For a community recipe outside the pretorin source tree, point the loader
at your recipe's directory:

```python
monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: my_recipe_parent)
```

## Validate as a Smoke Test

`pretorin recipe validate <id>` runs the manifest schema check, the script
existence check, and the description-quality check. Add it to your CI as
a shell-out smoke test:

```yaml
- name: Validate recipes
  run: |
    pretorin recipe validate my-recipe
    pretorin recipe validate my-other-recipe
```

This catches "you renamed the script and forgot to update the manifest"
faster than any pytest assertion will.

## What Not to Test

- **Don't test the platform API.** Your recipe is an adapter; testing
  what `create_evidence` does is pretorin's job, not yours. Mock the
  client.
- **Don't test pydantic validation of the manifest.** That's already
  covered by pretorin's loader tests. If your manifest is malformed,
  `pretorin recipe validate` will tell you.
- **Don't test redaction patterns.** Use `pretorin.evidence.redact`'s
  helpers and trust them.
