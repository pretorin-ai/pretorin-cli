"""Tests for recipe manifest pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pretorin.recipes.manifest import (
    RecipeManifest,
    RecipeParam,
    RecipeRequires,
    ScriptDecl,
)

# =============================================================================
# RecipeParam
# =============================================================================


def test_recipe_param_basic_string() -> None:
    p = RecipeParam(type="string", description="A test param")
    assert p.type == "string"
    assert p.required is False
    assert p.default is None


def test_recipe_param_required_with_default() -> None:
    p = RecipeParam(type="integer", description="With default", default=42, required=True)
    assert p.default == 42
    assert p.required is True


def test_recipe_param_array_with_items() -> None:
    p = RecipeParam(
        type="array",
        items={"type": "string"},
        description="Array param",
    )
    assert p.items == {"type": "string"}


def test_recipe_param_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        RecipeParam(type="object", description="Bad type")  # type: ignore[arg-type]


def test_recipe_param_rejects_empty_description() -> None:
    with pytest.raises(ValidationError):
        RecipeParam(type="string", description="")


# =============================================================================
# RecipeRequires
# =============================================================================


def test_recipe_requires_defaults_empty() -> None:
    r = RecipeRequires()
    assert r.cli == []
    assert r.env == []


def test_recipe_requires_with_cli_and_env() -> None:
    r = RecipeRequires(
        cli=[{"name": "inspec", "probe": "inspec --version"}],
        env=["GITHUB_TOKEN"],
    )
    assert r.cli[0]["name"] == "inspec"
    assert r.env == ["GITHUB_TOKEN"]


# =============================================================================
# ScriptDecl
# =============================================================================


def test_script_decl_basic() -> None:
    s = ScriptDecl(path="scripts/run.py", description="Run something")
    assert s.path == "scripts/run.py"
    assert s.timeout_seconds == 300
    assert s.writes_evidence is False
    assert s.params == {}


def test_script_decl_with_params() -> None:
    s = ScriptDecl(
        path="scripts/redact.py",
        description="Redact secrets",
        params={"text": RecipeParam(type="string", description="Raw text")},
    )
    assert "text" in s.params
    assert s.params["text"].type == "string"


def test_script_decl_writes_evidence_flag() -> None:
    s = ScriptDecl(path="scripts/x.py", description="X", writes_evidence=True)
    assert s.writes_evidence is True


def test_script_decl_rejects_zero_timeout() -> None:
    with pytest.raises(ValidationError):
        ScriptDecl(path="x.py", description="x", timeout_seconds=0)


def test_script_decl_rejects_empty_description() -> None:
    with pytest.raises(ValidationError):
        ScriptDecl(path="x.py", description="")


# =============================================================================
# RecipeManifest — required fields
# =============================================================================


def _valid_manifest_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "test-recipe",
        "version": "0.1.0",
        "name": "Test Recipe",
        "description": "A test recipe",
        "use_when": "Never; this is a test fixture.",
        "produces": "evidence",
        "author": "Test Author",
    }
    base.update(overrides)
    return base


def test_manifest_required_minimum_constructs() -> None:
    m = RecipeManifest(**_valid_manifest_kwargs())  # type: ignore[arg-type]
    assert m.id == "test-recipe"
    assert m.version == "0.1.0"
    assert m.tier == "community"  # default; loader overrides at parse time
    assert m.license == "Apache-2.0"  # default
    assert m.contract_version == 1
    assert m.recipe_schema_version == "1.0"
    assert m.attests == []
    assert m.params == {}
    assert m.scripts == {}


@pytest.mark.parametrize(
    "missing_field",
    ["id", "version", "name", "description", "use_when", "produces", "author"],
)
def test_manifest_rejects_missing_required(missing_field: str) -> None:
    kwargs = _valid_manifest_kwargs()
    del kwargs[missing_field]
    with pytest.raises(ValidationError):
        RecipeManifest(**kwargs)  # type: ignore[arg-type]


# =============================================================================
# RecipeManifest — id format and field validation
# =============================================================================


def test_manifest_rejects_uppercase_id() -> None:
    with pytest.raises(ValidationError):
        RecipeManifest(**_valid_manifest_kwargs(id="Test-Recipe"))  # type: ignore[arg-type]


def test_manifest_rejects_underscore_in_id() -> None:
    """Recipe ids are kebab-case to align with module naming and avoid OS case issues."""
    with pytest.raises(ValidationError):
        RecipeManifest(**_valid_manifest_kwargs(id="test_recipe"))  # type: ignore[arg-type]


def test_manifest_rejects_id_starting_with_digit() -> None:
    with pytest.raises(ValidationError):
        RecipeManifest(**_valid_manifest_kwargs(id="1test"))  # type: ignore[arg-type]


def test_manifest_accepts_valid_kebab_ids() -> None:
    for valid_id in ["a", "abc", "abc-def", "test-recipe-with-many-segments"]:
        m = RecipeManifest(**_valid_manifest_kwargs(id=valid_id))  # type: ignore[arg-type]
        assert m.id == valid_id


@pytest.mark.parametrize("produces", ["evidence", "narrative", "both"])
def test_manifest_accepts_all_produces_values(produces: str) -> None:
    m = RecipeManifest(**_valid_manifest_kwargs(produces=produces))  # type: ignore[arg-type]
    assert m.produces == produces


def test_manifest_rejects_unknown_produces() -> None:
    with pytest.raises(ValidationError):
        RecipeManifest(**_valid_manifest_kwargs(produces="something-else"))  # type: ignore[arg-type]


@pytest.mark.parametrize("tier", ["official", "partner", "community"])
def test_manifest_accepts_all_tiers(tier: str) -> None:
    m = RecipeManifest(**_valid_manifest_kwargs(tier=tier))  # type: ignore[arg-type]
    assert m.tier == tier


def test_manifest_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        RecipeManifest(**_valid_manifest_kwargs(tier="bogus"))  # type: ignore[arg-type]


def test_manifest_with_full_optional_fields() -> None:
    m = RecipeManifest(
        **_valid_manifest_kwargs(
            attests=[{"control": "AC-2", "framework": "nist-800-53-r5"}],
            params={"target": RecipeParam(type="string", description="Target")},
            requires=RecipeRequires(cli=[{"name": "inspec"}], env=["GH_TOKEN"]),
            scripts={"run": ScriptDecl(path="scripts/run.py", description="run")},
            license="MIT",
            min_pretorin_version="0.16.0",
        )  # type: ignore[arg-type]
    )
    assert m.attests[0]["control"] == "AC-2"
    assert m.requires.cli[0]["name"] == "inspec"
    assert m.scripts["run"].path == "scripts/run.py"
    assert m.license == "MIT"
    assert m.min_pretorin_version == "0.16.0"
