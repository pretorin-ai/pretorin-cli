"""Tests for context verify command and source attestation write guard."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from pretorin.attestation import (
    _MANIFEST_LOAD_CACHE,
    SourceIdentity,
    SourceLevel,
    SourceManifest,
    SourceRequirement,
    VerificationStatus,
    VerifiedSnapshot,
)
from pretorin.cli.context import _enforce_source_attestation

# Tests use _MANIFEST_LOAD_CACHE for cleanup only (via setup/teardown).

# ---------------------------------------------------------------------------
# Write guard tests
# ---------------------------------------------------------------------------


class TestEnforceSourceAttestation:
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

    def test_allows_when_no_snapshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)
        # No exception raised
        _enforce_source_attestation("sys-1", "fedramp-moderate", False)

    def test_allows_when_verified(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot()
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            _enforce_source_attestation("sys-1", "fedramp-moderate", False)

    def test_blocks_on_mismatch(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot()
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://different.com"

        from pretorin.client.api import PretorianClientError

        with patch("pretorin.client.config.Config", return_value=mock_config):
            with pytest.raises(PretorianClientError, match="Source attestation mismatch"):
                _enforce_source_attestation("sys-1", "fedramp-moderate", False)

    def test_allows_when_stale(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot(status=VerificationStatus.STALE)
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            _enforce_source_attestation("sys-1", "fedramp-moderate", False)

    def test_allows_when_partial(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot(status=VerificationStatus.PARTIAL)
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            _enforce_source_attestation("sys-1", "fedramp-moderate", False)

    def test_override_bypasses_check(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot()
        save_snapshot(snap)

        # Even with a mismatch url, override allows it
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://different.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            _enforce_source_attestation("sys-1", "fedramp-moderate", True)

    def test_system_scope_mismatch(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = self._make_snapshot(system_id="sys-1")
        save_snapshot(snap)

        # Loading snapshot for sys-2 returns None (different scope key), so it passes
        _enforce_source_attestation("sys-2", "fedramp-moderate", False)

    def test_allows_manual_source_snapshot(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        manual_source = SourceIdentity(
            provider_type="hris",
            identity="workday.acme.com/tenant/prod",
            display_name="Workday HRIS",
            raw={"attestation_type": "manual"},
        )
        snap = self._make_snapshot(sources=(manual_source,))
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            # Should not raise — manual sources pass enforcement
            _enforce_source_attestation("sys-1", "fedramp-moderate", False)


# ---------------------------------------------------------------------------
# Context clear / set snapshot invalidation tests
# ---------------------------------------------------------------------------


class TestContextClearDeletesSnapshot:
    def test_clears_snapshot(self, tmp_path, monkeypatch):
        from pretorin.attestation import save_snapshot

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        snap = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fw-1",
            api_base_url="url",
            sources=(),
            verified_at=datetime.now(timezone.utc).isoformat(),
        )
        save_snapshot(snap)

        # Verify snapshot exists
        from pretorin.attestation import load_snapshot

        assert load_snapshot("sys-1", "fw-1") is not None

        # Simulate context_clear logic
        from pretorin.attestation import delete_snapshot

        delete_snapshot("sys-1", "fw-1")
        assert load_snapshot("sys-1", "fw-1") is None


# ---------------------------------------------------------------------------
# run_command utility tests
# ---------------------------------------------------------------------------


class TestRunCommand:
    @pytest.mark.asyncio
    async def test_success(self):
        from pretorin.utils import run_command

        code, stdout, stderr = await run_command(["echo", "hello"])
        assert code == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_command_not_found(self):
        from pretorin.utils import run_command

        code, stdout, stderr = await run_command(["nonexistent_binary_xyz"])
        assert code == -1
        assert "not found" in stderr.lower() or "Command not found" in stderr


# ---------------------------------------------------------------------------
# Phase 3: Manifest write guard tests
# ---------------------------------------------------------------------------


class TestEnforceSourceAttestationWithManifest:
    """Test the manifest evaluation path in _enforce_source_attestation."""

    def _make_snapshot(self, sources=()):
        return VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fw-1",
            api_base_url="https://example.com",
            sources=sources,
            verified_at=datetime.now(timezone.utc).isoformat(),
            status=VerificationStatus.VERIFIED,
        )

    def _patch_snapshot_and_config(self, snapshot):
        """Return a context manager that patches snapshot loading and config."""
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        return (
            patch("pretorin.attestation.load_snapshot", return_value=snapshot),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.VERIFIED),
            patch("pretorin.client.config.Config", return_value=mock_config),
        )

    def setup_method(self):
        _MANIFEST_LOAD_CACHE.clear()

    def teardown_method(self):
        _MANIFEST_LOAD_CACHE.clear()

    def test_no_manifest_allows_write(self):
        snap = self._make_snapshot(sources=(SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),))
        p1, p2, p3 = self._patch_snapshot_and_config(snap)
        with p1, p2, p3, patch("pretorin.attestation.load_manifest", return_value=None):
            _enforce_source_attestation("sys-1", "fw-1", False)

    def test_satisfied_manifest_allows_write(self):
        snap = self._make_snapshot(sources=(SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),))
        manifest = SourceManifest(
            version="1",
            system_sources=(SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),),
        )
        p1, p2, p3 = self._patch_snapshot_and_config(snap)
        with p1, p2, p3, patch("pretorin.attestation.load_manifest", return_value=manifest):
            _enforce_source_attestation("sys-1", "fw-1", False)  # should not raise

    def test_unsatisfied_manifest_blocks_write(self):
        snap = self._make_snapshot(sources=(SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),))
        manifest = SourceManifest(
            version="1",
            system_sources=(SourceRequirement(source_type="hris", level=SourceLevel.REQUIRED),),
        )
        p1, p2, p3 = self._patch_snapshot_and_config(snap)
        from pretorin.client.api import PretorianClientError

        with p1, p2, p3, patch("pretorin.attestation.load_manifest", return_value=manifest):
            with pytest.raises(PretorianClientError, match="missing required sources.*hris"):
                _enforce_source_attestation("sys-1", "fw-1", False)

    def test_partial_manifest_allows_write_with_warning(self):
        snap = self._make_snapshot(sources=(SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),))
        manifest = SourceManifest(
            version="1",
            system_sources=(
                SourceRequirement(source_type="git_repo", level=SourceLevel.REQUIRED),
                SourceRequirement(source_type="hris", level=SourceLevel.RECOMMENDED),
            ),
        )
        p1, p2, p3 = self._patch_snapshot_and_config(snap)
        with p1, p2, p3, patch("pretorin.attestation.load_manifest", return_value=manifest):
            _enforce_source_attestation("sys-1", "fw-1", False)
        # Partial is allowed (not blocked), cache stores the manifest
        # Partial is allowed (not blocked) — write proceeds with warning

    def test_override_bypasses_manifest_check(self):
        """allow_unverified_sources=True skips all checks."""
        _enforce_source_attestation("sys-1", "fw-1", True)

    def test_mismatch_takes_priority_over_manifest(self):
        snap = self._make_snapshot()
        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        from pretorin.client.api import PretorianClientError

        with (
            patch("pretorin.attestation.load_snapshot", return_value=snap),
            patch("pretorin.attestation.check_snapshot_validity", return_value=VerificationStatus.MISMATCH),
            patch("pretorin.client.config.Config", return_value=mock_config),
        ):
            with pytest.raises(PretorianClientError, match="mismatch"):
                _enforce_source_attestation("sys-1", "fw-1", False)

    def test_no_snapshot_skips_manifest_check(self):
        with patch("pretorin.attestation.load_snapshot", return_value=None):
            _enforce_source_attestation("sys-1", "fw-1", False)

    def test_control_id_triggers_family_evaluation(self):
        snap = self._make_snapshot(sources=(SourceIdentity(provider_type="git_repo", identity="github.com/org/repo"),))
        manifest = SourceManifest(
            version="1",
            family_sources={
                "ac": (SourceRequirement(source_type="aws_identity", level=SourceLevel.REQUIRED),),
            },
        )
        p1, p2, p3 = self._patch_snapshot_and_config(snap)
        from pretorin.client.api import PretorianClientError

        with p1, p2, p3, patch("pretorin.attestation.load_manifest", return_value=manifest):
            with pytest.raises(PretorianClientError, match="aws_identity"):
                _enforce_source_attestation("sys-1", "fw-1", False, control_id="ac-02")
