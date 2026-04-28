"""Universal capture-rule enforcement on the pydantic write models.

When `code_file_path` is set:
1. The description must contain a fenced code block (rule).
2. The description must end with a `*Captured from <path> ...*`
   provenance footer; the validator auto-appends one when missing.

The rule lives on `EvidenceCreate` and `EvidenceBatchItemCreate` so
every write path (CLI, MCP, agent batch, campaign apply) trips it.
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from pretorin.client.models import EvidenceBatchItemCreate, EvidenceCreate

_VALID_FENCED_DESC = "Some prose.\n\n```yaml\nfoo: bar\n```"
_INVALID_PROSE_ONLY_DESC = "This evidence references the file but has no embedded snippet."


class TestEvidenceCreateCaptureRule:
    def test_no_code_file_path_passthrough(self):
        ev = EvidenceCreate(name="x", description="prose", evidence_type="other", source="cli")
        assert ev.description == "prose"

    def test_code_file_path_without_fenced_block_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            EvidenceCreate(
                name="x",
                description=_INVALID_PROSE_ONLY_DESC,
                evidence_type="code_snippet",
                source="cli",
                code_file_path="app/auth.py",
            )
        assert "no embedded fenced code block" in str(exc_info.value)
        assert "app/auth.py" in str(exc_info.value)

    def test_code_file_path_with_fenced_block_appends_provenance_footer(self):
        ev = EvidenceCreate(
            name="x",
            description=_VALID_FENCED_DESC,
            evidence_type="code_snippet",
            source="cli",
            code_file_path="config/db.yaml",
            code_line_numbers="10-30",
            code_commit_hash="abc1234",
        )
        # Validator auto-appends an italic provenance footer when
        # missing, so the AI-drafted description ends with the standard
        # footer line.
        assert ev.description.startswith(_VALID_FENCED_DESC.rstrip())
        assert "\n---\n" in ev.description
        last_line = [ln for ln in ev.description.splitlines() if ln.strip()][-1]
        assert last_line.startswith("*Captured from `config/db.yaml` lines 10-30")
        assert "commit `abc1234`" in last_line
        assert last_line.endswith("*")


class TestEvidenceBatchItemCreateCaptureRule:
    """The campaign apply path was the original bypass site. This test
    exercises the model the batch path constructs at
    `workflows/campaign.py:1511`."""

    def test_campaign_shape_without_fenced_block_rejected(self):
        with pytest.raises(ValidationError, match="no embedded fenced code block"):
            EvidenceBatchItemCreate(
                name="API autoscaling and resource limits (production)",
                description=(
                    "Capacity guardrails and autoscaling thresholds are defined "
                    "in production Helm values for the API service."
                ),
                control_id="ast-1",
                evidence_type="configuration",
                code_file_path="helm/values.production.yaml",
                code_line_numbers="1-20",
            )

    def test_campaign_shape_with_fenced_block_gets_footer(self):
        desc = (
            "Capacity guardrails and autoscaling thresholds are defined "
            "in production Helm values for the API service.\n\n"
            "```yaml\nresources:\n  requests:\n    cpu: 500m\n```"
        )
        item = EvidenceBatchItemCreate(
            name="API autoscaling and resource limits (production)",
            description=desc,
            control_id="ast-1",
            evidence_type="configuration",
            code_file_path="helm/values.production.yaml",
            code_line_numbers="1-20",
            code_commit_hash="284b1cb",
        )
        # Validator auto-appends the provenance footer with path / lines /
        # commit / RFC3339 UTC timestamp.
        assert "Capacity guardrails" in item.description
        assert "```yaml" in item.description
        assert "\n---\n" in item.description
        last_line = [ln for ln in item.description.splitlines() if ln.strip()][-1]
        assert "Captured from `helm/values.production.yaml` lines 1-20" in last_line
        assert "commit `284b1cb`" in last_line
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", last_line)

    def test_no_code_file_path_passthrough(self):
        item = EvidenceBatchItemCreate(
            name="x",
            description="just prose",
            control_id="cc1.1",
            evidence_type="other",
        )
        assert item.description == "just prose"

    def test_4_backtick_fence_recognized(self):
        desc = "prose\n\n````python\ncode here\n````"
        item = EvidenceBatchItemCreate(
            name="x",
            description=desc,
            control_id="cc1.1",
            evidence_type="code_snippet",
            code_file_path="app.py",
        )
        # Original description preserved + footer appended.
        assert item.description.startswith(desc)
        assert "Captured from `app.py`" in item.description

    def test_existing_footer_not_duplicated(self):
        desc = "prose\n\n```python\ncode\n```\n\n---\n*Captured from `app.py` · 2026-04-27T18:32:11Z*"
        item = EvidenceBatchItemCreate(
            name="x",
            description=desc,
            control_id="cc1.1",
            evidence_type="code_snippet",
            code_file_path="app.py",
        )
        assert item.description.count("*Captured from") == 1

    def test_tilde_fence_not_recognized(self):
        desc = "prose\n\n~~~python\nx = 1\n~~~"
        with pytest.raises(ValidationError, match="no embedded fenced code block"):
            EvidenceBatchItemCreate(
                name="x",
                description=desc,
                control_id="cc1.1",
                evidence_type="code_snippet",
                code_file_path="app.py",
            )
