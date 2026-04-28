"""Tests for pretorin.evidence.redact.

The redactor is intentionally narrow: API keys + password assignments,
nothing else. Vendor plugins from upstream tools and entropy heuristics
have been removed because they over-redacted real-world code/config.
"""

from __future__ import annotations

import logging
import re

import pytest

from pretorin.evidence import redact as redact_mod
from pretorin.evidence.redact import RedactionSummary, redact
from tests._synthetic_fixtures import (
    AWS_AKIA,
    AWS_ASIA,
    AWS_SECRET,
    GITHUB_PAT,
    GOOGLE_API_KEY,
    SLACK_TOKEN,
    STRIPE_LIVE_KEY,
    STRIPE_TEST_KEY,
)


@pytest.fixture(autouse=True)
def _reset_backend_log(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(redact_mod, "_BACKEND_LOGGED", False)


class TestSecretPatterns:
    def test_aws_access_key_redacted(self):
        out, summary = redact(f"key = {AWS_AKIA}")
        assert "AKIA" not in out
        assert "[REDACTED:aws_access_key]" in out
        assert summary.counts["aws_access_key"] == 1

    def test_aws_asia_token_redacted(self):
        out, summary = redact(f"token={AWS_ASIA}")
        assert "[REDACTED:aws_access_key]" in out
        assert summary.counts["aws_access_key"] == 1

    def test_aws_secret_key_redacted(self):
        out, summary = redact(f'aws_secret_access_key = "{AWS_SECRET}"')
        assert AWS_SECRET[:13] not in out
        # The keyword detector also fires on this line; that's fine —
        # both flag the same value as sensitive.
        assert summary.total >= 1

    def test_github_token_redacted(self):
        out, summary = redact(f"export TOKEN={GITHUB_PAT}")
        assert "ghp_" not in out
        assert summary.counts["github_token"] == 1

    def test_slack_token_redacted(self):
        out, summary = redact(f"SLACK={SLACK_TOKEN}")
        assert "[REDACTED:slack_token]" in out
        assert summary.counts["slack_token"] == 1

    def test_stripe_live_key_redacted(self):
        out, summary = redact(STRIPE_LIVE_KEY)
        assert "[REDACTED:stripe_key]" in out
        assert summary.counts["stripe_key"] == 1

    def test_stripe_test_key_redacted(self):
        out, summary = redact(f"STRIPE={STRIPE_TEST_KEY}")
        assert "[REDACTED:stripe_key]" in out
        assert summary.counts["stripe_key"] == 1

    def test_google_api_key_redacted(self):
        assert len(GOOGLE_API_KEY) == 39  # AIza (4) + 35-char body
        out, summary = redact(f"GOOGLE={GOOGLE_API_KEY}")
        assert "[REDACTED:google_api_key]" in out
        assert summary.counts["google_api_key"] == 1

    def test_jwt_redacted(self):
        out, summary = redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abcdefghij")
        assert "[REDACTED:jwt]" in out
        assert summary.counts["jwt"] == 1

    def test_pem_private_key_redacted(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAxxx\nyyy\nzzz\n-----END RSA PRIVATE KEY-----"
        out, summary = redact(text)
        assert "MIIEpAIBAAKCAQEA" not in out
        assert summary.counts["pem_private_key"] == 1

    def test_negative_aws_lookalike(self):
        out, summary = redact("AKIASHORT okay")
        assert "AKIASHORT" in out
        assert summary.counts["aws_access_key"] == 0


class TestPasswordKeyword:
    def test_password_assignment_redacted(self):
        out, summary = redact('password = "hunter2sosecure"')
        assert "hunter2sosecure" not in out
        assert "[REDACTED:password]" in out
        # Keyword stays readable so auditor knows what was redacted.
        assert "password = " in out
        assert summary.counts["password"] == 1

    def test_secret_keyword_redacted(self):
        out, summary = redact('secret: "mysuperdupersecretvalue"')
        assert "mysuperdupersecretvalue" not in out
        assert "[REDACTED:password]" in out
        assert summary.counts["password"] == 1

    def test_api_key_keyword_redacted(self):
        out, summary = redact('api_key = "abc1234567890def"')
        assert "abc1234567890def" not in out
        assert summary.counts["password"] == 1

    def test_access_token_keyword_redacted(self):
        out, summary = redact('access_token: "tokenvaluehere1234"')
        assert "tokenvaluehere1234" not in out
        assert summary.counts["password"] == 1

    def test_short_value_not_redacted(self):
        """Values under 4 chars are too short to be a real secret."""
        out, summary = redact('password = "x"')
        assert summary.counts["password"] == 0


class TestNoFalsePositivesOnConfig:
    """Regression: detect-secrets's HighEntropyString plugins flagged
    every YAML identifier ('resources', 'cpu', 'autoscaling', etc.) as
    a secret. The current pack must keep config content readable."""

    def test_yaml_config_unchanged(self):
        sample = (
            "resources:\n"
            "  requests:\n"
            "    cpu: 500m\n"
            "    memory: 512Mi\n"
            "autoscaling:\n"
            "  enabled: true\n"
            "  minReplicas: 2\n"
            "  maxReplicas: 5\n"
            "  targetCPUUtilizationPercentage: 70\n"
        )
        out, summary = redact(sample)
        assert out == sample
        assert not summary.any()

    def test_python_imports_unchanged(self):
        sample = (
            "import logging\n"
            "from collections import Counter\n"
            "from collections.abc import Callable\n"
            "from dataclasses import dataclass, field\n"
        )
        out, summary = redact(sample)
        assert out == sample
        assert not summary.any()

    def test_uuid_unchanged(self):
        out, summary = redact("system_id: 550e8400-e29b-41d4-a716-446655440000")
        assert "550e8400-e29b-41d4-a716-446655440000" in out
        assert not summary.any()

    def test_commit_hash_unchanged(self):
        out, summary = redact("commit: 7c2b59a8f9e3c4d2b1a0f8e7d6c5b4a3f2e1d0c9")
        assert "7c2b59a8f9e3c4d2b1a0f8e7d6c5b4a3f2e1d0c9" in out
        assert not summary.any()


class TestRedactSecretsToggle:
    def test_redact_disabled_returns_input(self):
        out, summary = redact(AWS_AKIA, redact_secrets=False)
        assert out == AWS_AKIA
        assert not summary.any()


class TestSummary:
    def test_short_form_singular(self):
        s = RedactionSummary()
        s.counts["aws_access_key"] = 1
        assert s.short_form() == "1 secret redacted"

    def test_short_form_plural(self):
        s = RedactionSummary()
        s.counts["aws_access_key"] = 2
        s.counts["github_token"] = 3
        assert s.short_form() == "5 secrets redacted"

    def test_short_form_empty(self):
        assert RedactionSummary().short_form() == ""

    def test_total_property(self):
        s = RedactionSummary()
        s.counts["aws_access_key"] = 2
        s.counts["password"] = 1
        assert s.total == 3


class TestStablePlaceholder:
    def test_placeholder_format(self):
        out, _ = redact(AWS_AKIA)
        assert re.search(r"\[REDACTED:aws_access_key]", out)


class TestBackendLogging:
    def test_active_backend_logged_at_info(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.INFO, logger="pretorin.evidence.redact"):
            redact("nothing here")
        assert any("internal_named_pack" in r.message for r in caplog.records)

    def test_disabled_backend_logged(self, caplog: pytest.LogCaptureFixture):
        with caplog.at_level(logging.INFO, logger="pretorin.evidence.redact"):
            redact("nothing here", redact_secrets=False)
        assert any("disabled" in r.message for r in caplog.records)
