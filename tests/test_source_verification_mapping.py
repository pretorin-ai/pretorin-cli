"""Tests for source verification mapping (attestation.py).

Covers: build_source_verification(), extract_git_context_from_snapshot(),
source_role on SourceIdentity, PROVIDER_TO_CANONICAL_SOURCE_TYPE mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from pretorin.attestation import (
    PROVIDER_TO_CANONICAL_SOURCE_TYPE,
    SourceIdentity,
    VerificationStatus,
    VerifiedSnapshot,
    build_source_verification,
    extract_git_context_from_snapshot,
)


def _make_snapshot(
    status: VerificationStatus = VerificationStatus.VERIFIED,
    sources: list[SourceIdentity] | None = None,
) -> VerifiedSnapshot:
    """Build a test snapshot."""
    return VerifiedSnapshot(
        system_id="sys-1",
        framework_id="fedramp-moderate",
        verified_at=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
        ttl_seconds=3600,
        sources=sources
        or [
            SourceIdentity(
                provider_type="git_repo",
                identity="https://github.com/test/repo",
                source_role="code",
                raw={"remote_url": "https://github.com/test/repo", "head_commit": "abc123def"},
            ),
        ],
        status=status.value,
        api_base_url="https://api.test",
    )


class TestProviderToCanonicalSourceType:
    def test_git_repo_maps_to_github_repo(self) -> None:
        assert PROVIDER_TO_CANONICAL_SOURCE_TYPE["git_repo"] == "github_repo"

    def test_aws_identity_maps_to_aws_account(self) -> None:
        assert PROVIDER_TO_CANONICAL_SOURCE_TYPE["aws_identity"] == "aws_account"

    def test_azure_identity_maps_to_entra_tenant(self) -> None:
        assert PROVIDER_TO_CANONICAL_SOURCE_TYPE["azure_identity"] == "entra_tenant"

    def test_k8s_context_maps_to_kubernetes_cluster(self) -> None:
        assert PROVIDER_TO_CANONICAL_SOURCE_TYPE["k8s_context"] == "kubernetes_cluster"


class TestSourceIdentityRole:
    def test_git_provider_sets_code_role(self) -> None:
        si = SourceIdentity(
            provider_type="git_repo",
            identity="https://github.com/test/repo",
            source_role="code",
        )
        assert si.source_role == "code"

    def test_default_role_is_empty(self) -> None:
        si = SourceIdentity(provider_type="test", identity="test")
        assert si.source_role == ""


class TestBuildSourceVerification:
    def test_returns_none_when_no_snapshot(self) -> None:
        with patch("pretorin.attestation.load_snapshot", return_value=None):
            result = build_source_verification("sys-1", "fedramp-moderate")
        assert result is None

    def test_returns_none_when_unverified(self) -> None:
        snapshot = _make_snapshot(status=VerificationStatus.UNVERIFIED)
        with (
            patch("pretorin.attestation.load_snapshot", return_value=snapshot),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.UNVERIFIED),
            patch("pretorin.client.config.Config"),
        ):
            result = build_source_verification("sys-1", "fedramp-moderate")
        assert result is None

    def test_verified_snapshot_returns_correct_payload(self) -> None:
        snapshot = _make_snapshot(status=VerificationStatus.VERIFIED)
        with (
            patch("pretorin.attestation.load_snapshot", return_value=snapshot),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.VERIFIED),
            patch("pretorin.client.config.Config"),
        ):
            result = build_source_verification("sys-1", "fedramp-moderate")

        assert result is not None
        assert result["overall_state"] == "verified"
        assert result["verified_at"] is not None
        assert result["ttl_seconds"] == 3600
        assert len(result["sources"]) == 1

        src = result["sources"][0]
        assert src["source_type"] == "github_repo"
        assert src["source_role"] == "code"
        assert src["identifier"] == "https://github.com/test/repo"
        assert src["verified"] is True

    def test_unknown_provider_maps_to_custom(self) -> None:
        snapshot = _make_snapshot(
            sources=[
                SourceIdentity(
                    provider_type="unknown_provider",
                    identity="test-identity",
                    source_role="monitoring",
                ),
            ]
        )
        with (
            patch("pretorin.attestation.load_snapshot", return_value=snapshot),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.VERIFIED),
            patch("pretorin.client.config.Config"),
        ):
            result = build_source_verification("sys-1", "fedramp-moderate")

        assert result is not None
        assert result["sources"][0]["source_type"] == "custom"

    def test_empty_role_defaults_to_monitoring(self) -> None:
        snapshot = _make_snapshot(
            sources=[
                SourceIdentity(
                    provider_type="git_repo",
                    identity="https://github.com/test/repo",
                    source_role="",
                ),
            ]
        )
        with (
            patch("pretorin.attestation.load_snapshot", return_value=snapshot),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.VERIFIED),
            patch("pretorin.client.config.Config"),
        ):
            result = build_source_verification("sys-1", "fedramp-moderate")

        assert result["sources"][0]["source_role"] == "monitoring"


class TestExtractGitContext:
    def test_returns_none_when_no_snapshot(self) -> None:
        with patch("pretorin.attestation.load_snapshot", return_value=None):
            result = extract_git_context_from_snapshot("sys-1", "fedramp-moderate")
        assert result is None

    def test_extracts_repo_and_commit(self) -> None:
        snapshot = _make_snapshot()
        with patch("pretorin.attestation.load_snapshot", return_value=snapshot):
            result = extract_git_context_from_snapshot("sys-1", "fedramp-moderate")

        assert result is not None
        assert result["code_repository"] == "https://github.com/test/repo"
        assert result["code_commit_hash"] == "abc123def"

    def test_returns_none_when_no_git_provider(self) -> None:
        snapshot = _make_snapshot(
            sources=[
                SourceIdentity(
                    provider_type="aws_identity",
                    identity="arn:aws:iam::123456:root",
                    source_role="identity",
                ),
            ]
        )
        with patch("pretorin.attestation.load_snapshot", return_value=snapshot):
            result = extract_git_context_from_snapshot("sys-1", "fedramp-moderate")
        assert result is None
