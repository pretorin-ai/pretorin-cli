"""Tests for the issue #88 hard rule pre-check at the workflow boundary.

The universal enforcement lives on the pydantic models in
`pretorin.client.models`. This shim runs the same check earlier so
direct callers of `compliance_updates.upsert_evidence` get a Python
ValueError instead of a deeper pydantic ValidationError.
"""

from __future__ import annotations

import pytest

from pretorin.workflows.compliance_updates import _enforce_capture_attached


class TestEnforceCapture:
    def test_no_code_context_passthrough(self):
        assert _enforce_capture_attached("just prose", {}) == "just prose"

    def test_code_file_without_fenced_block_rejected(self):
        with pytest.raises(ValueError, match="no embedded fenced code block"):
            _enforce_capture_attached(
                "User prose with no snippet.",
                {"code_file_path": "app/auth.py"},
            )

    def test_code_file_with_fenced_block_appends_footer(self):
        desc = "TOTP-based MFA verification.\n\n```python\ndef verify(): pass\n```"
        out = _enforce_capture_attached(
            desc,
            {
                "code_file_path": "app/auth.py",
                "code_line_numbers": "12-14",
                "code_commit_hash": "abc1234",
            },
        )
        assert out.startswith(desc.rstrip())
        assert "\n---\n" in out
        assert "Captured from `app/auth.py` lines 12-14" in out
        assert "commit `abc1234`" in out

    def test_code_context_without_code_file_path_passthrough(self):
        desc = "Just prose, no snippet."
        out = _enforce_capture_attached(
            desc,
            {"code_repository": "https://github.com/foo/bar", "code_commit_hash": "abc1234"},
        )
        assert out == desc

    def test_error_message_names_the_offending_file(self):
        with pytest.raises(ValueError, match="auth.py"):
            _enforce_capture_attached("plain prose", {"code_file_path": "auth.py"})

    def test_error_message_suggests_remediation(self):
        with pytest.raises(ValueError, match="`pretorin evidence upsert --code-file"):
            _enforce_capture_attached("plain prose", {"code_file_path": "auth.py"})
