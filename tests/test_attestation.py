"""Tests for source attestation models, providers, and persistence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.attestation import (
    _AUTO_PROVIDER_REGISTRY,
    _MANIFEST_LOAD_CACHE,
    AWSIdentityProvider,
    AzureIdentityProvider,
    GitRepoProvider,
    KubernetesContextProvider,
    ManifestResult,
    ManifestStatus,
    ManualAttestationProvider,
    SourceIdentity,
    SourceLevel,
    SourceManifest,
    SourceProvider,
    SourceRequirement,
    VerificationStatus,
    VerifiedSnapshot,
    _collect_requirements,
    _matches_requirement,
    _parse_manifest,
    _requirement_from_dict,
    build_write_provenance,
    check_snapshot_validity,
    delete_snapshot,
    evaluate_manifest,
    extract_family_from_control_id,
    load_manifest,
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


# ---------------------------------------------------------------------------
# Phase 3: Manifest model tests
# ---------------------------------------------------------------------------


class TestSourceLevel:
    def test_enum_values(self):
        assert SourceLevel.REQUIRED == "required"
        assert SourceLevel.RECOMMENDED == "recommended"
        assert SourceLevel.OPTIONAL == "optional"

    def test_from_string(self):
        assert SourceLevel("required") == SourceLevel.REQUIRED


class TestSourceRequirementModels:
    def test_frozen_dataclass(self):
        req = SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED)
        assert req.source_type == "git_repo"
        assert req.level == SourceLevel.REQUIRED
        assert req.identity_pattern is None
        assert req.account_id is None
        assert req.description == ""

    def test_with_all_fields(self):
        req = SourceRequirement(
            source_type="aws_identity",
            level=SourceLevel.REQUIRED,
            identity_pattern="arn:aws:iam::123",
            account_id="123456789012",
            description="Prod AWS account",
        )
        assert req.account_id == "123456789012"
        assert req.description == "Prod AWS account"


class TestManifestStatusEnum:
    def test_enum_values(self):
        assert ManifestStatus.SATISFIED == "satisfied"
        assert ManifestStatus.UNSATISFIED == "unsatisfied"
        assert ManifestStatus.PARTIAL == "partial"
        assert ManifestStatus.NO_MANIFEST == "no_manifest"


class TestManifestResult:
    def test_default_construction(self):
        result = ManifestResult(status=ManifestStatus.SATISFIED)
        assert result.satisfied == ()
        assert result.missing_required == ()
        assert result.missing_recommended == ()
        assert result.warnings == ()


# ---------------------------------------------------------------------------
# Phase 3: Manifest parsing tests
# ---------------------------------------------------------------------------


class TestRequirementFromDict:
    def test_valid_entry(self):
        req = _requirement_from_dict({"source_type": "git_repo", "level": "required"})
        assert req is not None
        assert req.source_type == "git_repo"
        assert req.level == SourceLevel.REQUIRED

    def test_with_all_fields(self):
        req = _requirement_from_dict({
            "source_type": "aws_identity",
            "level": "recommended",
            "identity_pattern": "arn:aws:iam::123",
            "account_id": "123",
            "description": "AWS prod",
        })
        assert req is not None
        assert req.identity_pattern == "arn:aws:iam::123"
        assert req.account_id == "123"

    def test_missing_source_type_returns_none(self):
        req = _requirement_from_dict({"level": "required"})
        assert req is None

    def test_unknown_level_returns_none(self):
        req = _requirement_from_dict({"source_type": "git_repo", "level": "mandatory"})
        assert req is None

    def test_minimal_entry(self):
        req = _requirement_from_dict({"source_type": "hris", "level": "optional"})
        assert req is not None
        assert req.level == SourceLevel.OPTIONAL


class TestParseManifest:
    def test_valid_manifest(self):
        data = {
            "version": "1",
            "system_sources": [
                {"source_type": "git_repo", "level": "required"},
            ],
            "family_sources": {
                "ac": [{"source_type": "aws_identity", "level": "required"}],
            },
        }
        manifest = _parse_manifest(data)
        assert manifest is not None
        assert manifest.version == "1"
        assert len(manifest.system_sources) == 1
        assert "ac" in manifest.family_sources

    def test_missing_version_returns_none(self):
        data = {"system_sources": [{"source_type": "git_repo", "level": "required"}]}
        assert _parse_manifest(data) is None

    def test_malformed_entries_skipped(self):
        data = {
            "version": "1",
            "system_sources": [
                {"source_type": "git_repo", "level": "required"},  # valid
                {"source_type": "aws", "level": "bogus"},  # bad level, skipped
                {"level": "required"},  # no source_type, skipped
            ],
        }
        manifest = _parse_manifest(data)
        assert manifest is not None
        assert len(manifest.system_sources) == 1

    def test_unsupported_version_returns_none(self):
        data = {"version": "2", "system_sources": [{"source_type": "git_repo", "level": "required"}]}
        assert _parse_manifest(data) is None

    def test_empty_system_sources(self):
        manifest = _parse_manifest({"version": "1"})
        assert manifest is not None
        assert manifest.system_sources == ()

    def test_family_keys_lowercased(self):
        data = {
            "version": "1",
            "family_sources": {"AC": [{"source_type": "aws_identity", "level": "required"}]},
        }
        manifest = _parse_manifest(data)
        assert manifest is not None
        assert "ac" in manifest.family_sources
        assert "AC" not in manifest.family_sources


# ---------------------------------------------------------------------------
# Phase 3: Manifest loading tests
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def _make_manifest_json(self):
        return json.dumps({
            "version": "1",
            "system_sources": [{"source_type": "git_repo", "level": "required"}],
        })

    def test_env_var_json_string(self, monkeypatch):
        monkeypatch.setenv("PRETORIN_SOURCE_MANIFEST", self._make_manifest_json())
        manifest = load_manifest("sys-1")
        assert manifest is not None
        assert manifest.version == "1"

    def test_env_var_file_path(self, tmp_path, monkeypatch):
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(self._make_manifest_json())
        monkeypatch.setenv("PRETORIN_SOURCE_MANIFEST", str(manifest_file))
        manifest = load_manifest("sys-1")
        assert manifest is not None

    def test_repo_local_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
        pretorin_dir = tmp_path / ".pretorin"
        pretorin_dir.mkdir()
        (pretorin_dir / "source-manifest.json").write_text(self._make_manifest_json())
        with patch("pretorin.attestation._get_git_root", return_value=tmp_path):
            manifest = load_manifest("sys-1")
        assert manifest is not None

    def test_user_config_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
        monkeypatch.setattr("pretorin.attestation.CONFIG_DIR", tmp_path)
        (tmp_path / "source-manifest-sys-1.json").write_text(self._make_manifest_json())
        with patch("pretorin.attestation._get_git_root", return_value=None):
            manifest = load_manifest("sys-1")
        assert manifest is not None

    def test_inline_config(self, monkeypatch):
        monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
        inline = {"version": "1", "system_sources": [{"source_type": "git_repo", "level": "required"}]}
        mock_config = MagicMock()
        mock_config.source_manifest = inline
        with (
            patch("pretorin.attestation._get_git_root", return_value=None),
            patch("pretorin.client.config.Config", return_value=mock_config),
        ):
            manifest = load_manifest("sys-1")
        assert manifest is not None

    def test_no_manifest_returns_none(self, monkeypatch):
        monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
        mock_config = MagicMock()
        mock_config.source_manifest = None
        with (
            patch("pretorin.attestation._get_git_root", return_value=None),
            patch("pretorin.client.config.Config", return_value=mock_config),
        ):
            manifest = load_manifest("sys-1")
        assert manifest is None

    def test_precedence_env_over_repo(self, tmp_path, monkeypatch):
        # Env var has git_repo, repo-local has aws_identity
        monkeypatch.setenv(
            "PRETORIN_SOURCE_MANIFEST",
            json.dumps({
                "version": "1",
                "system_sources": [{"source_type": "git_repo", "level": "required"}],
            }),
        )
        pretorin_dir = tmp_path / ".pretorin"
        pretorin_dir.mkdir()
        (pretorin_dir / "source-manifest.json").write_text(
            json.dumps({
                "version": "1",
                "system_sources": [{"source_type": "aws_identity", "level": "required"}],
            })
        )
        manifest = load_manifest("sys-1")
        assert manifest is not None
        assert manifest.system_sources[0].source_type == "git_repo"

    def test_bad_json_env_var_returns_none(self, monkeypatch):
        monkeypatch.setenv("PRETORIN_SOURCE_MANIFEST", "not-json-not-file")
        mock_config = MagicMock()
        mock_config.source_manifest = None
        with (
            patch("pretorin.attestation._get_git_root", return_value=None),
            patch("pretorin.client.config.Config", return_value=mock_config),
        ):
            manifest = load_manifest("sys-1")
        assert manifest is None

    def test_git_root_failure_skips_repo(self, monkeypatch):
        monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
        mock_config = MagicMock()
        mock_config.source_manifest = None
        with (
            patch("pretorin.attestation._get_git_root", return_value=None),
            patch("pretorin.client.config.Config", return_value=mock_config),
        ):
            manifest = load_manifest("sys-1")
        assert manifest is None


# ---------------------------------------------------------------------------
# Phase 3: Requirement matching tests
# ---------------------------------------------------------------------------


class TestMatchesRequirement:
    def test_type_match(self):
        src = SourceIdentity(provider_type="git_repo", identity="github.com/org/repo")
        req = SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED)
        assert _matches_requirement(src, req) is True

    def test_type_mismatch(self):
        src = SourceIdentity(provider_type="aws_identity", identity="arn:123")
        req = SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED)
        assert _matches_requirement(src, req) is False

    def test_identity_pattern_exact_match(self):
        src = SourceIdentity(provider_type="git_repo", identity="github.com/org/repo")
        req = SourceRequirement(
            source_type="git_repo", level=SourceLevel.REQUIRED, identity_pattern="github.com/org/repo"
        )
        assert _matches_requirement(src, req) is True

    def test_identity_pattern_segment_match(self):
        src = SourceIdentity(provider_type="git_repo", identity="github.com/org/repo")
        req = SourceRequirement(
            source_type="git_repo", level=SourceLevel.REQUIRED, identity_pattern="github.com/org"
        )
        assert _matches_requirement(src, req) is True

    def test_identity_pattern_no_match_org_malicious(self):
        """Anchored matching prevents org-malicious from matching org."""
        src = SourceIdentity(provider_type="git_repo", identity="github.com/org-malicious/repo")
        req = SourceRequirement(
            source_type="git_repo", level=SourceLevel.REQUIRED, identity_pattern="github.com/org"
        )
        assert _matches_requirement(src, req) is False

    def test_account_id_match(self):
        src = SourceIdentity(
            provider_type="aws_identity", identity="arn:123", account_id="123456789012"
        )
        req = SourceRequirement(
            source_type="aws_identity", level=SourceLevel.REQUIRED, account_id="123456789012"
        )
        assert _matches_requirement(src, req) is True

    def test_account_id_mismatch(self):
        src = SourceIdentity(
            provider_type="aws_identity", identity="arn:123", account_id="999999999999"
        )
        req = SourceRequirement(
            source_type="aws_identity", level=SourceLevel.REQUIRED, account_id="123456789012"
        )
        assert _matches_requirement(src, req) is False

    def test_combined_identity_and_account_id(self):
        """Account_id alone is sufficient for AWS matching (no identity_pattern needed)."""
        src = SourceIdentity(
            provider_type="aws_identity",
            identity="arn:aws:iam::123456789012:root",
            account_id="123456789012",
        )
        req = SourceRequirement(
            source_type="aws_identity",
            level=SourceLevel.REQUIRED,
            account_id="123456789012",
        )
        assert _matches_requirement(src, req) is True

    def test_identity_pattern_with_colon_separator(self):
        """ARNs use ':' not '/' — use exact match or account_id for AWS."""
        src = SourceIdentity(
            provider_type="aws_identity",
            identity="arn:aws:iam::123456789012:root",
            account_id="123456789012",
        )
        # identity_pattern with ARN prefix won't match because ARNs use ':'
        req = SourceRequirement(
            source_type="aws_identity",
            level=SourceLevel.REQUIRED,
            identity_pattern="arn:aws:iam::123456789012",
        )
        # The anchored match uses '/' — ARN colons don't match
        assert _matches_requirement(src, req) is False


# ---------------------------------------------------------------------------
# Phase 3: Requirement collection tests
# ---------------------------------------------------------------------------


class TestCollectRequirements:
    def test_system_only(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
            ),
        )
        reqs = _collect_requirements(manifest)
        assert len(reqs) == 1
        assert reqs[0].source_type == "git_repo"

    def test_system_plus_family(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
            ),
            family_sources={
                "ac": (SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),),
            },
        )
        reqs = _collect_requirements(manifest, family_id="ac")
        types = {r.source_type for r in reqs}
        assert types == {"git_repo", "aws_identity"}

    def test_stricter_level_wins(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="aws_identity", level=SourceLevel.RECOMMENDED),
            ),
            family_sources={
                "ac": (SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),),
            },
        )
        reqs = _collect_requirements(manifest, family_id="ac")
        assert len(reqs) == 1
        assert reqs[0].level == SourceLevel.REQUIRED

    def test_unknown_family_returns_system_only(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
            ),
            family_sources={
                "ac": (SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),),
            },
        )
        reqs = _collect_requirements(manifest, family_id="zz")
        assert len(reqs) == 1
        assert reqs[0].source_type == "git_repo"


# ---------------------------------------------------------------------------
# Phase 3: Manifest evaluation tests
# ---------------------------------------------------------------------------


class TestEvaluateManifest:
    def _git_source(self):
        return SourceIdentity(provider_type="git_repo", identity="github.com/org/repo")

    def _aws_source(self):
        return SourceIdentity(provider_type="aws_identity", identity="arn:123", account_id="123456")

    def test_all_required_present_returns_satisfied(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
            ),
        )
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.SATISFIED
        assert len(result.satisfied) == 1
        assert len(result.missing_required) == 0

    def test_missing_required_returns_unsatisfied(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="hris", level=SourceLevel.REQUIRED),
            ),
        )
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.UNSATISFIED
        assert len(result.missing_required) == 1
        assert result.missing_required[0].source_type == "hris"

    def test_required_present_recommended_missing_returns_partial(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
                SourceRequirement(source_type="hris", level=SourceLevel.RECOMMENDED),
            ),
        )
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.PARTIAL
        assert len(result.missing_recommended) == 1

    def test_all_optional_missing_returns_satisfied(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
                SourceRequirement(source_type="lms", level=SourceLevel.OPTIONAL),
            ),
        )
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.SATISFIED

    def test_empty_manifest_returns_satisfied(self):
        manifest = SourceManifest(version="1")
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.SATISFIED

    def test_family_level_evaluation(self):
        manifest = SourceManifest(
            version="1",
            family_sources={
                "ac": (SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),),
            },
        )
        # Without AWS source, ac family evaluation fails
        result = evaluate_manifest(manifest, (self._git_source(),), family_id="ac")
        assert result.status == ManifestStatus.UNSATISFIED

        # With AWS source, passes
        result = evaluate_manifest(manifest, (self._git_source(), self._aws_source()), family_id="ac")
        assert result.status == ManifestStatus.SATISFIED

    def test_identity_enforcement(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(
                    source_type="git_repo",
                    level=SourceLevel.REQUIRED,
                    identity_pattern="github.com/org/repo",
                ),
            ),
        )
        wrong_repo = SourceIdentity(provider_type="git_repo", identity="github.com/other/repo")
        result = evaluate_manifest(manifest, (wrong_repo,))
        assert result.status == ManifestStatus.UNSATISFIED

    def test_manual_attestation_satisfies_requirement(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="hris", level=SourceLevel.REQUIRED),
            ),
        )
        manual = SourceIdentity(
            provider_type="hris",
            identity="workday.acme.com",
            raw={"attestation_type": "manual"},
        )
        result = evaluate_manifest(manifest, (manual,))
        assert result.status == ManifestStatus.SATISFIED

    def test_multiple_required_partially_missing(self):
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
                SourceRequirement(source_type="hris", level=SourceLevel.REQUIRED),
                SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),
            ),
        )
        result = evaluate_manifest(manifest, (self._git_source(),))
        assert result.status == ManifestStatus.UNSATISFIED
        missing_types = {r.source_type for r in result.missing_required}
        assert missing_types == {"hris", "aws_identity"}


# ---------------------------------------------------------------------------
# Phase 3: Family extraction tests
# ---------------------------------------------------------------------------


class TestExtractFamily:
    def test_nist_format(self):
        assert extract_family_from_control_id("ac-02") == "ac"

    def test_nist_uppercase(self):
        assert extract_family_from_control_id("SC-07") == "sc"

    def test_nist_enhancement(self):
        assert extract_family_from_control_id("ac-02.1") == "ac"

    def test_cmmc_format(self):
        assert extract_family_from_control_id("AC.L2-3.1.1") == "ac"

    def test_800_171r3_format(self):
        assert extract_family_from_control_id("03.01.01") == "ac"

    def test_800_171r3_cm(self):
        assert extract_family_from_control_id("06.01.02") == "cm"

    def test_none_input(self):
        assert extract_family_from_control_id(None) is None

    def test_empty_string(self):
        assert extract_family_from_control_id("") is None

    def test_unrecognized_format(self):
        assert extract_family_from_control_id("something-else") is None


# ---------------------------------------------------------------------------
# Phase 3: Manifest cache tests
# ---------------------------------------------------------------------------


class TestManifestLoadCache:
    def setup_method(self):
        _MANIFEST_LOAD_CACHE.clear()

    def test_cache_stores_manifest(self):
        manifest = SourceManifest(version="1")
        _MANIFEST_LOAD_CACHE["sys-1"] = manifest
        assert _MANIFEST_LOAD_CACHE.get("sys-1") is manifest

    def test_cache_miss_returns_none(self):
        assert _MANIFEST_LOAD_CACHE.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Phase 3: Provenance with manifest tests
# ---------------------------------------------------------------------------


class TestProvenanceWithManifest:
    """Test that build_write_provenance includes manifest evaluation."""

    def _save_verified_snapshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        snapshot = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fw",
            api_base_url="https://platform.pretorin.com/api/v1/public",
            sources=(
                SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),
            ),
            verified_at=datetime.now(timezone.utc).isoformat(),
            status=VerificationStatus.VERIFIED,
        )
        save_snapshot(snapshot)

    def test_manifest_status_in_provenance_from_cache(self, tmp_path, monkeypatch):
        self._save_verified_snapshot(tmp_path, monkeypatch)
        _MANIFEST_LOAD_CACHE.clear()
        # Cache a SourceManifest (not ManifestResult) — provenance evaluates fresh
        _MANIFEST_LOAD_CACHE["sys-1"] = SourceManifest(
            version="1",
            system_sources=(SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),),
        )
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://platform.pretorin.com/api/v1/public"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            result = build_write_provenance("sys-1", "fw")
        # Snapshot has git_repo source, manifest requires git_repo → satisfied
        assert result["manifest_status"] == "satisfied"
        _MANIFEST_LOAD_CACHE.clear()

    def test_no_manifest_status(self, tmp_path, monkeypatch):
        self._save_verified_snapshot(tmp_path, monkeypatch)
        _MANIFEST_LOAD_CACHE.clear()
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://platform.pretorin.com/api/v1/public"
        mock_config.source_manifest = None
        with (
            patch("pretorin.client.config.Config", return_value=mock_config),
            patch("pretorin.attestation._get_git_root", return_value=None),
        ):
            monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
            result = build_write_provenance("sys-1", "fw")
        assert result["manifest_status"] == "no_manifest"
        _MANIFEST_LOAD_CACHE.clear()

    def test_missing_required_in_provenance(self, tmp_path, monkeypatch):
        self._save_verified_snapshot(tmp_path, monkeypatch)
        _MANIFEST_LOAD_CACHE.clear()
        # Cache a manifest that requires hris (not detected in snapshot)
        _MANIFEST_LOAD_CACHE["sys-1"] = SourceManifest(
            version="1",
            system_sources=(SourceRequirement(source_type="hris", level=SourceLevel.REQUIRED),),
        )
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://platform.pretorin.com/api/v1/public"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            result = build_write_provenance("sys-1", "fw")
        assert result["manifest_status"] == "unsatisfied"
        assert result["missing_required_sources"] == ["hris"]
        _MANIFEST_LOAD_CACHE.clear()

    def test_backward_compat_no_control_id(self, tmp_path, monkeypatch):
        """build_write_provenance without control_id still works."""
        self._save_verified_snapshot(tmp_path, monkeypatch)
        _MANIFEST_LOAD_CACHE.clear()
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://platform.pretorin.com/api/v1/public"
        mock_config.source_manifest = None
        with (
            patch("pretorin.client.config.Config", return_value=mock_config),
            patch("pretorin.attestation._get_git_root", return_value=None),
        ):
            monkeypatch.delenv("PRETORIN_SOURCE_MANIFEST", raising=False)
            result = build_write_provenance("sys-1", "fw")
        assert "verification_status" in result
        _MANIFEST_LOAD_CACHE.clear()
