"""Tests for evidence_validation.py — campaign apply pre-write enrichment.

Post-rework 2026-04-27: ``enrich_evidence_recommendations`` is the
campaign / agent / MCP equivalent of the CLI's `_maybe_capture` helper.
For each recommendation with a real file path, it reads the slice,
redacts secrets, and rewrites ``description`` with the snippet embedded
inline. The structured ``code_snippet`` field is cleared per decision Q2
(snippet body lives only in description).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pretorin.evidence import redact as redact_mod
from pretorin.workflows.evidence_validation import (
    enrich_evidence_recommendations,
    validate_code_reference,
)
from tests._synthetic_fixtures import AWS_AKIA


@pytest.fixture(autouse=True)
def _reset_backend_log(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(redact_mod, "_BACKEND_LOGGED", False)


class TestValidateCodeReferenceLegacy:
    """The legacy shim is kept for non-campaign callers. Returns a dict
    with code_file_path / code_line_numbers only — no snippet body
    (Q2: snippet lives in the description, not as a structured field)."""

    def test_returns_none_when_no_file_path(self):
        assert validate_code_reference(None, None, Path("/tmp")) is None

    def test_returns_none_when_file_missing(self, tmp_path: Path):
        assert validate_code_reference("nonexistent.py", None, tmp_path) is None

    def test_returns_context_with_valid_file(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\n")
        result = validate_code_reference("test.py", None, tmp_path)
        assert result is not None
        assert result["code_file_path"] == "test.py"
        assert "code_snippet" not in result

    def test_keeps_line_range_when_valid(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("alpha\nbeta\ngamma\n")
        result = validate_code_reference("test.py", "2-3", tmp_path)
        assert result is not None
        assert result["code_line_numbers"] == "2-3"

    def test_drops_invalid_line_format(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("a\nb\n")
        result = validate_code_reference("test.py", "abc", tmp_path)
        assert result is not None
        assert "code_line_numbers" not in result

    def test_path_traversal_blocked(self, tmp_path: Path):
        secret = tmp_path.parent / "secret.txt"
        secret.write_text("secret")
        try:
            assert validate_code_reference("../secret.txt", None, tmp_path) is None
        finally:
            try:
                secret.unlink()
            except FileNotFoundError:
                pass

    def test_symlink_traversal_blocked(self, tmp_path: Path):
        target = tmp_path.parent / "secret-link-target.txt"
        target.write_text("secret")
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        try:
            assert validate_code_reference("link.txt", None, tmp_path) is None
        finally:
            try:
                target.unlink()
            except FileNotFoundError:
                pass


class TestEnrichEvidenceRecommendations:
    def test_embeds_snippet_into_description_when_ai_did_not(self, tmp_path: Path):
        """The user's bug: AI-drafted prose without a fenced block.
        Enricher reads the file and rewrites description with the
        snippet inline. Source provenance lives on the structured
        columns of the API record, not in the description."""
        f = tmp_path / "config.yaml"
        f.write_text("key: value\nother: data\n")
        recs = [
            {
                "name": "Config",
                "description": "Capacity guardrails are defined in production Helm values.",
                "code_file_path": "config.yaml",
                "code_line_numbers": "1-2",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        desc = recs[0]["description"]
        assert "Capacity guardrails" in desc
        assert "```yaml" in desc
        assert "key: value" in desc
        # Provenance footer at the end of the description.
        assert "Captured from `config.yaml` lines 1-2" in desc
        # Structured field stays populated with the redacted snippet
        # (carries forward the prior behavior, just redacted now).
        assert recs[0]["code_snippet"] == "key: value\nother: data"

    def test_redacts_secrets_in_embedded_snippet(self, tmp_path: Path):
        f = tmp_path / "secrets.py"
        f.write_text(f"AWS_KEY = '{AWS_AKIA}'\n")
        recs = [
            {
                "name": "Auth key reference",
                "description": "AWS access key for the audit logger.",
                "code_file_path": "secrets.py",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        desc = recs[0]["description"]
        assert AWS_AKIA not in desc
        assert "[REDACTED:aws_access_key]" in desc
        assert "1 secret redacted" in desc
        # The structured field also gets the redacted form (security
        # improvement vs the prior raw-content behavior).
        assert AWS_AKIA not in recs[0]["code_snippet"]
        assert "[REDACTED:aws_access_key]" in recs[0]["code_snippet"]

    def test_keeps_ai_fenced_block_unchanged(self, tmp_path: Path):
        """If the AI already drafted a description with a fenced block,
        the enricher leaves it alone. The pydantic validator on
        EvidenceCreate / EvidenceBatchItemCreate auto-prepends the
        Source prelude when the model is constructed."""
        f = tmp_path / "config.yaml"
        f.write_text("key: value\n")
        ai_drafted = "Auto-scaling settings.\n\n```yaml\nresources:\n  cpu: 500m\n```"
        recs = [
            {
                "name": "Cfg",
                "description": ai_drafted,
                "code_file_path": "config.yaml",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        # AI's description preserved verbatim — the validator will add
        # the Source prelude downstream.
        assert recs[0]["description"] == ai_drafted
        # Structured field still gets the redacted snippet from the file.
        assert "key: value" in recs[0]["code_snippet"]

    def test_drops_invalid_reference(self, tmp_path: Path):
        recs = [
            {
                "name": "Missing",
                "description": "prose",
                "code_file_path": "nope.py",
                "code_line_numbers": "1-5",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        # All code fields dropped so the record passes validation as a
        # plain text evidence item.
        assert "code_file_path" not in recs[0]
        assert "code_line_numbers" not in recs[0]
        assert "code_snippet" not in recs[0]
        assert recs[0]["description"] == "prose"

    def test_leaves_recs_without_file_path_unchanged(self, tmp_path: Path):
        recs = [{"name": "Policy", "description": "A policy doc"}]
        enrich_evidence_recommendations(recs, tmp_path)
        assert recs[0] == {"name": "Policy", "description": "A policy doc"}

    def test_out_of_bounds_line_range_falls_back_to_whole_file(self, tmp_path: Path):
        """When the AI's reported line range is wrong, enricher captures
        the whole file rather than dropping the reference outright."""
        f = tmp_path / "small.py"
        f.write_text("a = 1\nb = 2\n")
        recs = [
            {
                "name": "x",
                "description": "Small config file.",
                "code_file_path": "small.py",
                "code_line_numbers": "100-200",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        desc = recs[0]["description"]
        assert "Small config file." in desc
        assert "a = 1" in desc
        # Bad range got dropped; structured column carries no line_numbers.
        assert "code_line_numbers" not in recs[0]

    def test_mixed_valid_and_invalid(self, tmp_path: Path):
        f = tmp_path / "real.py"
        f.write_text("print('hello')\n")
        recs = [
            {"name": "Valid", "description": "real one", "code_file_path": "real.py"},
            {"name": "Invalid", "description": "ref to missing", "code_file_path": "fake.py"},
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        assert "real one" in recs[0]["description"]
        assert "print('hello')" in recs[0]["description"]
        assert "code_file_path" not in recs[1]


class TestCampaignBatchEndToEnd:
    """The original bypass site: build the same shape that
    `workflows/campaign.py:1511` constructs, and confirm the resulting
    EvidenceBatchItemCreate model is valid."""

    def test_valid_pipeline_through_to_model(self, tmp_path: Path):
        from pretorin.client.models import EvidenceBatchItemCreate

        f = tmp_path / "values.production.yaml"
        f.write_text("autoscaling:\n  enabled: true\n  minReplicas: 2\n")
        recs = [
            {
                "name": "API autoscaling and resource limits (production)",
                "description": "Capacity guardrails for the API service.",
                "evidence_type": "configuration",
                "control_id": "ast-1",
                "code_file_path": "values.production.yaml",
                "code_line_numbers": "1-3",
                "code_commit_hash": "284b1cb",
            }
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        rec = recs[0]
        # The model construction is what campaign.py:1511 does.
        item = EvidenceBatchItemCreate(
            name=rec["name"],
            description=rec["description"],
            control_id=rec["control_id"],
            evidence_type=rec["evidence_type"],
            code_file_path=rec.get("code_file_path"),
            code_line_numbers=rec.get("code_line_numbers"),
            code_commit_hash=rec.get("code_commit_hash"),
        )
        # Pydantic validator passed: description has fenced block AND a
        # provenance footer with path/lines/commit/timestamp.
        assert "```yaml" in item.description
        assert "minReplicas: 2" in item.description
        assert "Captured from `values.production.yaml`" in item.description
        assert "commit `284b1cb`" in item.description
        assert item.code_file_path == "values.production.yaml"
        assert item.code_commit_hash == "284b1cb"
