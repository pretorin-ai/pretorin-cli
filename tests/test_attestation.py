"""Tests for source attestation models, providers, and persistence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.attestation import (
    _AUTO_PROVIDER_REGISTRY,
    AWSIdentityProvider,
    AzureIdentityProvider,
    GitRepoProvider,
    KubernetesContextProvider,
    ManualAttestationProvider,
    SourceIdentity,
    SourceProvider,
    VerificationStatus,
    VerifiedSnapshot,
    build_write_provenance,
    check_snapshot_validity,
    delete_snapshot,
    load_snapshot,
    resolve_providers,
    run_all_providers,
    save_snapshot,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestVerificationStatus:
    def test_enum_values(self):
        assert VerificationStatus.VERIFIED == "verified"
        assert VerificationStatus.PARTIAL == "partial"
        assert VerificationStatus.MISMATCH == "mismatch"
        assert VerificationStatus.STALE == "stale"
        assert VerificationStatus.UNVERIFIED == "unverified"

    def test_from_string(self):
        assert VerificationStatus("verified") == VerificationStatus.VERIFIED
        assert VerificationStatus("mismatch") == VerificationStatus.MISMATCH


class TestSourceIdentity:
    def test_creation(self):
        src = SourceIdentity(
            provider_type="git_repo",
            identity="https://github.com/org/repo.git",
            display_name="org/repo",
        )
        assert src.provider_type == "git_repo"
        assert src.identity == "https://github.com/org/repo.git"
        assert src.account_id is None
        assert src.raw == {}

    def test_frozen(self):
        src = SourceIdentity(provider_type="git_repo", identity="x")
        with pytest.raises(AttributeError):
            src.identity = "y"  # type: ignore[misc]


class TestVerifiedSnapshot:
    def test_creation(self):
        snap = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            api_base_url="https://platform.pretorin.com/api/v1/public",
            sources=(),
            verified_at="2026-04-13T00:00:00+00:00",
        )
        assert snap.system_id == "sys-1"
        assert snap.ttl_seconds == 3600
        assert snap.status == VerificationStatus.VERIFIED

    def test_frozen(self):
        snap = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fw",
            api_base_url="url",
            sources=(),
            verified_at="now",
        )
        with pytest.raises(AttributeError):
            snap.system_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Provider tests
# ---------------------------------------------------------------------------


class TestGitRepoProvider:
    @pytest.mark.asyncio
    async def test_detect_success(self):
        async def mock_cmd(cmd, timeout=10):
            if "remote" in cmd:
                return (0, "https://github.com/org/repo.git\n", "")
            if "rev-parse" in cmd:
                return (0, "abc123\n", "")
            return (-1, "", "")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            provider = GitRepoProvider()
            result = await provider.detect()

        assert result is not None
        assert result.provider_type == "git_repo"
        assert result.identity == "https://github.com/org/repo.git"
        assert result.raw["head_commit"] == "abc123"

    @pytest.mark.asyncio
    async def test_detect_not_a_repo(self):
        async def mock_cmd(cmd, timeout=10):
            return (128, "", "fatal: not a git repository")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await GitRepoProvider().detect()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_git_not_installed(self):
        async def mock_cmd(cmd, timeout=10):
            return (-1, "", "Command not found: git")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await GitRepoProvider().detect()

        assert result is None


class TestAWSIdentityProvider:
    @pytest.mark.asyncio
    async def test_detect_success(self):
        caller_identity = json.dumps({"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/test"})

        async def mock_cmd(cmd, timeout=10):
            return (0, caller_identity, "")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AWSIdentityProvider().detect()

        assert result is not None
        assert result.provider_type == "aws_identity"
        assert result.account_id == "123456789012"

    @pytest.mark.asyncio
    async def test_detect_not_configured(self):
        async def mock_cmd(cmd, timeout=10):
            return (255, "", "Unable to locate credentials")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AWSIdentityProvider().detect()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_aws_not_installed(self):
        async def mock_cmd(cmd, timeout=10):
            return (-1, "", "Command not found: aws")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AWSIdentityProvider().detect()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_invalid_json(self):
        async def mock_cmd(cmd, timeout=10):
            return (0, "not json", "")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AWSIdentityProvider().detect()

        assert result is None


class TestAzureIdentityProvider:
    @pytest.mark.asyncio
    async def test_detect_success(self):
        account_data = json.dumps({"id": "sub-123", "name": "My Sub", "tenantId": "tenant-456"})

        async def mock_cmd(cmd, timeout=10):
            return (0, account_data, "")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AzureIdentityProvider().detect()

        assert result is not None
        assert result.provider_type == "azure_identity"
        assert result.identity == "sub-123"
        assert result.account_id == "tenant-456"

    @pytest.mark.asyncio
    async def test_detect_not_logged_in(self):
        async def mock_cmd(cmd, timeout=10):
            return (1, "", "Please run 'az login'")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await AzureIdentityProvider().detect()

        assert result is None


class TestKubernetesContextProvider:
    @pytest.mark.asyncio
    async def test_detect_success(self):
        async def mock_cmd(cmd, timeout=10):
            if "current-context" in cmd:
                return (0, "minikube\n", "")
            if "view" in cmd:
                return (0, json.dumps({"kind": "Config"}), "")
            return (-1, "", "")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await KubernetesContextProvider().detect()

        assert result is not None
        assert result.provider_type == "k8s_context"
        assert result.identity == "minikube"

    @pytest.mark.asyncio
    async def test_detect_no_context(self):
        async def mock_cmd(cmd, timeout=10):
            return (1, "", "error: current-context is not set")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await KubernetesContextProvider().detect()

        assert result is None

    @pytest.mark.asyncio
    async def test_detect_kubectl_not_installed(self):
        async def mock_cmd(cmd, timeout=10):
            return (-1, "", "Command not found: kubectl")

        with patch("pretorin.attestation.run_command", side_effect=mock_cmd):
            result = await KubernetesContextProvider().detect()

        assert result is None


class TestManualAttestationProvider:
    @pytest.mark.asyncio
    async def test_provider_type_returns_source_type(self):
        provider = ManualAttestationProvider(source_type="hris", identity="workday.acme.com")
        assert provider.provider_type == "hris"

    @pytest.mark.asyncio
    async def test_detect_returns_identity(self):
        provider = ManualAttestationProvider(
            source_type="hris",
            identity="workday.acme.com/tenant/prod",
            display_name="Workday HRIS",
            account_id="acme-prod",
        )
        result = await provider.detect()
        assert result is not None
        assert result.provider_type == "hris"
        assert result.identity == "workday.acme.com/tenant/prod"
        assert result.display_name == "Workday HRIS"
        assert result.account_id == "acme-prod"

    @pytest.mark.asyncio
    async def test_detect_empty_identity_returns_none(self):
        provider = ManualAttestationProvider(source_type="idp", identity="")
        result = await provider.detect()
        assert result is None

    @pytest.mark.asyncio
    async def test_raw_contains_attestation_type(self):
        provider = ManualAttestationProvider(source_type="lms", identity="knowbe4.com")
        result = await provider.detect()
        assert result is not None
        assert result.raw["attestation_type"] == "manual"

    @pytest.mark.asyncio
    async def test_various_source_types(self):
        for stype in ("hris", "lms", "ticketing", "idp", "physical_access", "pam"):
            provider = ManualAttestationProvider(source_type=stype, identity=f"example.com/{stype}")
            result = await provider.detect()
            assert result is not None
            assert result.provider_type == stype


class TestProviderRegistry:
    def test_builtin_types_registered(self):
        assert "git_repo" in _AUTO_PROVIDER_REGISTRY
        assert "aws_identity" in _AUTO_PROVIDER_REGISTRY
        assert "azure_identity" in _AUTO_PROVIDER_REGISTRY
        assert "k8s_context" in _AUTO_PROVIDER_REGISTRY

    def test_resolve_no_config_returns_four_autodetect(self):
        providers = resolve_providers(None)
        types = {p.provider_type for p in providers}
        assert types == {"git_repo", "aws_identity", "azure_identity", "k8s_context"}

    def test_resolve_from_config_auto_entries(self):
        config = [{"type": "git_repo"}, {"type": "aws_identity"}]
        providers = resolve_providers(config)
        assert len(providers) == 2
        types = {p.provider_type for p in providers}
        assert types == {"git_repo", "aws_identity"}

    def test_resolve_disabled_entry_skipped(self):
        config = [
            {"type": "git_repo", "enabled": False},
            {"type": "aws_identity"},
        ]
        providers = resolve_providers(config)
        assert len(providers) == 1
        assert providers[0].provider_type == "aws_identity"

    def test_resolve_manual_entries(self):
        config = [
            {
                "type": "manual",
                "source_type": "hris",
                "identity": "workday.acme.com",
                "display_name": "Workday HRIS",
            }
        ]
        providers = resolve_providers(config)
        assert len(providers) == 1
        assert providers[0].provider_type == "hris"

    def test_resolve_mixed_auto_and_manual(self):
        config = [
            {"type": "git_repo"},
            {
                "type": "manual",
                "source_type": "idp",
                "identity": "okta.acme.com",
                "display_name": "Okta IdP",
            },
        ]
        providers = resolve_providers(config)
        assert len(providers) == 2
        types = {p.provider_type for p in providers}
        assert types == {"git_repo", "idp"}

    def test_resolve_unknown_type_warns(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            providers = resolve_providers([{"type": "nonexistent_provider"}])
        assert len(providers) == 0
        assert "Unknown provider type" in caplog.text

    def test_resolve_empty_list_returns_empty(self):
        providers = resolve_providers([])
        assert providers == []

    def test_resolve_manual_missing_fields_warns(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            providers = resolve_providers([{"type": "manual", "source_type": "hris"}])
        assert len(providers) == 0
        assert "missing source_type/identity" in caplog.text


class TestRunAllProviders:
    @pytest.mark.asyncio
    async def test_returns_detected_only(self):
        git = SourceIdentity(provider_type="git_repo", identity="repo")

        async def mock_git_detect():
            return git

        async def mock_fail_detect():
            return None

        p1 = AsyncMock(spec=SourceProvider)
        p1.detect = mock_git_detect
        p2 = AsyncMock(spec=SourceProvider)
        p2.detect = mock_fail_detect

        results = await run_all_providers([p1, p2])
        assert len(results) == 1
        assert results[0].provider_type == "git_repo"

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        async def exploding_detect():
            raise RuntimeError("boom")

        p = AsyncMock(spec=SourceProvider)
        p.detect = exploding_detect

        results = await run_all_providers([p])
        assert results == []

    @pytest.mark.asyncio
    async def test_reads_config_when_no_providers_given(self):
        mock_config = MagicMock()
        mock_config.source_providers = [{"type": "manual", "source_type": "hris", "identity": "workday.acme.com"}]
        with patch("pretorin.client.config.Config", return_value=mock_config):
            results = await run_all_providers()
        assert len(results) == 1
        assert results[0].provider_type == "hris"

    @pytest.mark.asyncio
    async def test_backward_compat_no_config(self):
        mock_config = MagicMock()
        mock_config.source_providers = None
        with patch("pretorin.client.config.Config", return_value=mock_config):
            with patch("pretorin.attestation.run_command", return_value=(-1, "", "not found")):
                results = await run_all_providers()
        assert results == []


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestSnapshotPersistence:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        source = SourceIdentity(
            provider_type="git_repo",
            identity="https://github.com/org/repo.git",
            raw={"head_commit": "abc"},
        )
        now = datetime.now(timezone.utc).isoformat()
        snap = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            api_base_url="https://example.com",
            sources=(source,),
            verified_at=now,
            ttl_seconds=3600,
            status=VerificationStatus.VERIFIED,
            cli_version="0.14.0",
        )

        save_snapshot(snap)
        loaded = load_snapshot("sys-1", "fedramp-moderate")

        assert loaded is not None
        assert loaded.system_id == "sys-1"
        assert loaded.framework_id == "fedramp-moderate"
        assert loaded.status == VerificationStatus.VERIFIED
        assert len(loaded.sources) == 1
        assert loaded.sources[0].provider_type == "git_repo"
        assert loaded.sources[0].identity == "https://github.com/org/repo.git"

    def test_load_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        assert load_snapshot("nonexistent", "fw") is None

    def test_load_malformed_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        path = tmp_path / "verified_context_sys_fw.json"
        path.write_text("not json{{{")
        assert load_snapshot("sys", "fw") is None

    def test_load_expired_ttl(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        data = {
            "system_id": "sys",
            "framework_id": "fw",
            "api_base_url": "url",
            "sources": [],
            "verified_at": old_time,
            "ttl_seconds": 3600,
            "status": "verified",
        }
        path = tmp_path / "verified_context_sys_fw.json"
        path.write_text(json.dumps(data))
        assert load_snapshot("sys", "fw") is None

    def test_delete_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        path = tmp_path / "verified_context_sys_fw.json"
        path.write_text("{}")
        assert delete_snapshot("sys", "fw") is True
        assert not path.exists()

    def test_delete_nonexistent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        assert delete_snapshot("sys", "fw") is False


# ---------------------------------------------------------------------------
# Validity check tests
# ---------------------------------------------------------------------------


class TestCheckSnapshotValidity:
    def _make_snapshot(self, **overrides):
        defaults = {
            "system_id": "sys-1",
            "framework_id": "fedramp-moderate",
            "api_base_url": "https://example.com",
            "sources": (),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "status": VerificationStatus.VERIFIED,
        }
        defaults.update(overrides)
        return VerifiedSnapshot(**defaults)

    def test_matching(self):
        snap = self._make_snapshot()
        status = check_snapshot_validity(snap, "sys-1", "fedramp-moderate", "https://example.com")
        assert status == VerificationStatus.VERIFIED

    def test_system_mismatch(self):
        snap = self._make_snapshot()
        status = check_snapshot_validity(snap, "sys-OTHER", "fedramp-moderate", "https://example.com")
        assert status == VerificationStatus.MISMATCH

    def test_framework_mismatch(self):
        snap = self._make_snapshot()
        status = check_snapshot_validity(snap, "sys-1", "nist-800-171", "https://example.com")
        assert status == VerificationStatus.MISMATCH

    def test_api_url_mismatch(self):
        snap = self._make_snapshot()
        status = check_snapshot_validity(snap, "sys-1", "fedramp-moderate", "https://other.com")
        assert status == VerificationStatus.MISMATCH

    def test_trailing_slash_normalization(self):
        snap = self._make_snapshot(api_base_url="https://example.com/")
        status = check_snapshot_validity(snap, "sys-1", "fedramp-moderate", "https://example.com")
        assert status == VerificationStatus.VERIFIED

    def test_partial_status_preserved(self):
        snap = self._make_snapshot(status=VerificationStatus.PARTIAL)
        status = check_snapshot_validity(snap, "sys-1", "fedramp-moderate", "https://example.com")
        assert status == VerificationStatus.PARTIAL


# ---------------------------------------------------------------------------
# Write provenance tests
# ---------------------------------------------------------------------------


class TestBuildWriteProvenance:
    def _save_verified_snapshot(self, tmp_path, monkeypatch, **overrides):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        source = SourceIdentity(
            provider_type="git_repo",
            identity="https://github.com/org/repo.git",
        )
        defaults = {
            "system_id": "sys-1",
            "framework_id": "fedramp-moderate",
            "api_base_url": "https://example.com",
            "sources": (source,),
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "status": VerificationStatus.VERIFIED,
            "cli_version": "0.14.0",
        }
        defaults.update(overrides)
        snap = VerifiedSnapshot(**defaults)
        save_snapshot(snap)
        return snap

    def test_no_snapshot_returns_unverified(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        result = build_write_provenance("sys-1", "fedramp-moderate")
        assert result["verification_status"] == "unverified"
        assert result["source"] == "pretorin-cli"
        assert "cli_version" in result
        assert "verified_at" not in result

    def test_valid_snapshot_returns_verified(self, tmp_path, monkeypatch):
        self._save_verified_snapshot(tmp_path, monkeypatch)
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            result = build_write_provenance("sys-1", "fedramp-moderate")
        assert result["verification_status"] == "verified"
        assert result["verified_at"] is not None
        assert len(result["verified_sources"]) == 1
        assert result["verified_sources"][0]["provider_type"] == "git_repo"

    def test_expired_snapshot_returns_unverified(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        data = {
            "system_id": "sys-1",
            "framework_id": "fw",
            "api_base_url": "url",
            "sources": [],
            "verified_at": old_time,
            "ttl_seconds": 3600,
            "status": "verified",
        }
        path = tmp_path / "verified_context_sys-1_fw.json"
        path.write_text(json.dumps(data))
        # load_snapshot returns None for expired, so provenance is unverified
        result = build_write_provenance("sys-1", "fw")
        assert result["verification_status"] == "unverified"

    def test_mismatched_api_url_returns_mismatch(self, tmp_path, monkeypatch):
        self._save_verified_snapshot(tmp_path, monkeypatch)
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://different.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            result = build_write_provenance("sys-1", "fedramp-moderate")
        assert result["verification_status"] == "mismatch"
