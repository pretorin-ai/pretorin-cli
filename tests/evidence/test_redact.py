"""Tests for evidence/redact.py.

Ported from PR #92's redactor scope. Synthetic secret-shaped values are
assembled via string concatenation so GitHub's push-protection scanner
doesn't pattern-match canonical public docs example values.
"""

from __future__ import annotations

import pytest

from pretorin.client.models import RedactionSummary
from pretorin.evidence.redact import RedactionResult, redact

# Synthetic fixtures (assembled at runtime so the file source itself doesn't
# match push-protection scanners).
_AWS_AKID = "AKIA" + "ABCDE0123456789Z"  # AKIA + exactly 16 uppercase-alnum chars
_AWS_SECRET_LINE = "aws_secret_access_key=" + ("a" * 40)
_GH_TOKEN = "ghp_" + ("Q" * 40)
_SLACK_TOKEN = "xoxb-" + ("0" * 12) + "-test"
_STRIPE_KEY = "sk_test_" + ("X" * 28)
_GOOGLE_KEY = "AIza" + ("X" * 35)
# JWT pattern requires ≥8 url-safe chars in each of the 3 dot-separated parts.
_JWT = "eyJ" + ("a" * 10) + ".eyJ" + ("b" * 10) + "." + ("c" * 10)
_PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAfake_key_body\n-----END RSA PRIVATE KEY-----"


# =============================================================================
# RedactionResult
# =============================================================================


def test_redaction_result_empty_defaults() -> None:
    r = RedactionResult()
    assert r.total == 0
    assert r.any() is False
    assert r.short_form() == ""


def test_redaction_result_short_form_singular_vs_plural() -> None:
    r = RedactionResult()
    r.counts["aws_access_key"] = 1
    assert r.short_form() == "1 secret redacted"
    r.counts["github_token"] = 2
    assert r.short_form() == "3 secrets redacted"


def test_redaction_result_to_audit_summary_empty() -> None:
    r = RedactionResult()
    summary = r.to_audit_summary()
    assert isinstance(summary, RedactionSummary)
    assert summary.secrets == 0
    assert summary.details is None


def test_redaction_result_to_audit_summary_with_counts() -> None:
    r = RedactionResult()
    r.counts["aws_access_key"] = 2
    r.counts["github_token"] = 1
    summary = r.to_audit_summary()
    assert summary.secrets == 3
    assert summary.details == {"aws_access_key": 2, "github_token": 1}


# =============================================================================
# redact() — secret patterns
# =============================================================================


def test_redact_aws_access_key() -> None:
    text = f"key = {_AWS_AKID}"
    redacted, result = redact(text)
    assert _AWS_AKID not in redacted
    assert "[REDACTED:aws_access_key]" in redacted
    assert result.counts["aws_access_key"] == 1


def test_redact_aws_secret_key() -> None:
    redacted, result = redact(_AWS_SECRET_LINE)
    assert "[REDACTED:aws_secret_key]" in redacted
    assert result.counts["aws_secret_key"] >= 1


def test_redact_github_token() -> None:
    redacted, result = redact(f"token: {_GH_TOKEN}")
    assert _GH_TOKEN not in redacted
    assert "[REDACTED:github_token]" in redacted


def test_redact_slack_token() -> None:
    redacted, result = redact(f"slack: {_SLACK_TOKEN}-extension")
    assert "xoxb-" not in redacted
    assert "[REDACTED:slack_token]" in redacted


def test_redact_stripe_key() -> None:
    redacted, result = redact(f"stripe: {_STRIPE_KEY}")
    assert _STRIPE_KEY not in redacted
    assert "[REDACTED:stripe_key]" in redacted


def test_redact_google_api_key() -> None:
    redacted, result = redact(f"google: {_GOOGLE_KEY}")
    assert _GOOGLE_KEY not in redacted
    assert "[REDACTED:google_api_key]" in redacted


def test_redact_jwt() -> None:
    redacted, result = redact(f"auth: Bearer {_JWT}")
    assert _JWT not in redacted
    assert "[REDACTED:jwt]" in redacted


def test_redact_pem_private_key() -> None:
    redacted, result = redact(_PEM)
    assert "fake_key_body" not in redacted
    assert "[REDACTED:pem_private_key]" in redacted


def test_redact_cred_url() -> None:
    text = "DATABASE_URL=postgres://admin:hunter2@db.example.com/main"
    redacted, result = redact(text)
    assert "hunter2" not in redacted
    assert "[REDACTED:cred_url]" in redacted


# =============================================================================
# redact() — password assignment patterns
# =============================================================================


@pytest.mark.parametrize(
    "line",
    [
        'password = "supersecret123"',
        "password: 'supersecret123'",
        'API_KEY="abcd1234abcd1234"',
        "auth_token: 'verylongtokenvalue'",
        'pwd="hunter2_long_enough"',
    ],
)
def test_redact_password_assignment(line: str) -> None:
    redacted, result = redact(line)
    assert "[REDACTED:password]" in redacted
    assert result.counts["password"] >= 1


def test_redact_password_keeps_keyword_visible() -> None:
    """Auditor sees `password = "[REDACTED:password]"` not just `[REDACTED:password]`."""
    redacted, _ = redact('password = "supersecret123"')
    assert "password" in redacted
    assert "[REDACTED:password]" in redacted
    assert "supersecret123" not in redacted


def test_redact_no_match_in_normal_code() -> None:
    """The Layer-1 reason this redactor exists: don't false-positive on real code.

    'cpu' / 'resources' / 'minReplicas' should NOT be flagged. A representative
    Helm-style YAML chunk passes through unchanged.
    """
    text = """
spec:
  replicas: 3
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    minReplicas: 1
"""
    redacted, result = redact(text)
    assert redacted == text
    assert result.total == 0


# =============================================================================
# redact() — disable flag
# =============================================================================


def test_redact_disabled_passthrough() -> None:
    """`--no-redact` exposes redact_secrets=False; input passes through unchanged."""
    text = f"key = {_AWS_AKID}"
    redacted, result = redact(text, redact_secrets=False)
    assert redacted == text
    assert result.total == 0


# =============================================================================
# Multiple secrets in one body
# =============================================================================


def test_redact_multiple_kinds_in_one_pass() -> None:
    text = f'AWS={_AWS_AKID}\nGH={_GH_TOKEN}\npassword = "hunter2_long"'
    redacted, result = redact(text)
    assert _AWS_AKID not in redacted
    assert _GH_TOKEN not in redacted
    assert "hunter2_long" not in redacted
    summary = result.to_audit_summary()
    assert summary.secrets == 3
    assert summary.details == {"aws_access_key": 1, "github_token": 1, "password": 1}
