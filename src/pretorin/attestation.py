"""Source attestation: models, providers, and snapshot persistence.

Verifies that the CLI session is connected to the expected external sources
(git repo, cloud account, k8s cluster) before allowing compliance writes.
Phase 1 detects session drift; Phase 3 adds correctness checking via source manifests.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pretorin.client.config import CONFIG_DIR
from pretorin.utils import run_command

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = CONFIG_DIR

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class VerificationStatus(str, Enum):
    """Overall verification state of a session."""

    VERIFIED = "verified"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    STALE = "stale"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class SourceIdentity:
    """Single verified source identity."""

    provider_type: str
    identity: str
    account_id: str | None = None
    display_name: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerifiedSnapshot:
    """TTL-bound attestation of verified execution context."""

    system_id: str
    framework_id: str
    api_base_url: str
    sources: tuple[SourceIdentity, ...]
    verified_at: str
    ttl_seconds: int = 3600
    status: VerificationStatus = VerificationStatus.VERIFIED
    cli_version: str = ""


# ---------------------------------------------------------------------------
# Source providers
# ---------------------------------------------------------------------------


class SourceProvider(ABC):
    """Abstract base for source identity providers."""

    @property
    @abstractmethod
    def provider_type(self) -> str: ...

    @abstractmethod
    async def detect(self) -> SourceIdentity | None: ...


class GitRepoProvider(SourceProvider):
    """Detect the current git repository identity."""

    @property
    def provider_type(self) -> str:
        return "git_repo"

    async def detect(self) -> SourceIdentity | None:
        code, remote_url, _ = await run_command(["git", "remote", "get-url", "origin"], timeout=30)
        if code != 0:
            return None

        remote = remote_url.strip()
        code2, head, _ = await run_command(["git", "rev-parse", "HEAD"], timeout=30)
        commit = head.strip() if code2 == 0 else ""

        return SourceIdentity(
            provider_type=self.provider_type,
            identity=remote,
            display_name=remote,
            raw={"remote_url": remote, "head_commit": commit},
        )


class AWSIdentityProvider(SourceProvider):
    """Detect the current AWS caller identity."""

    @property
    def provider_type(self) -> str:
        return "aws_identity"

    async def detect(self) -> SourceIdentity | None:
        code, stdout, _ = await run_command(["aws", "sts", "get-caller-identity", "--output", "json"], timeout=30)
        if code != 0:
            return None

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return None

        account_id = data.get("Account", "")
        arn = data.get("Arn", "")
        return SourceIdentity(
            provider_type=self.provider_type,
            identity=arn,
            account_id=account_id,
            display_name=f"AWS {account_id}",
            raw=data,
        )


class AzureIdentityProvider(SourceProvider):
    """Detect the current Azure subscription identity."""

    @property
    def provider_type(self) -> str:
        return "azure_identity"

    async def detect(self) -> SourceIdentity | None:
        code, stdout, _ = await run_command(["az", "account", "show", "--output", "json"], timeout=30)
        if code != 0:
            return None

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return None

        subscription_id = data.get("id", "")
        name = data.get("name", "")
        tenant_id = data.get("tenantId", "")
        return SourceIdentity(
            provider_type=self.provider_type,
            identity=subscription_id,
            account_id=tenant_id,
            display_name=f"Azure {name}" if name else f"Azure {subscription_id}",
            raw=data,
        )


class KubernetesContextProvider(SourceProvider):
    """Detect the current Kubernetes context."""

    @property
    def provider_type(self) -> str:
        return "k8s_context"

    async def detect(self) -> SourceIdentity | None:
        code, stdout, _ = await run_command(["kubectl", "config", "current-context"], timeout=30)
        if code != 0:
            return None

        context_name = stdout.strip()
        if not context_name:
            return None

        code2, cluster_info, _ = await run_command(["kubectl", "config", "view", "--minify", "-o", "json"], timeout=30)
        raw: dict[str, Any] = {"context": context_name}
        if code2 == 0:
            try:
                raw = json.loads(cluster_info)
                raw["context"] = context_name
            except json.JSONDecodeError:
                pass

        return SourceIdentity(
            provider_type=self.provider_type,
            identity=context_name,
            display_name=f"k8s:{context_name}",
            raw=raw,
        )


class ManualAttestationProvider(SourceProvider):
    """Human-declared source attestation from config.

    Supports arbitrary source_type values (hris, lms, idp, pam,
    physical_access, ticketing, etc.) — not limited to infrastructure.
    """

    def __init__(
        self,
        source_type: str,
        identity: str,
        display_name: str = "",
        account_id: str | None = None,
    ) -> None:
        self._source_type = source_type
        self._identity = identity
        self._display_name = display_name or identity
        self._account_id = account_id

    @property
    def provider_type(self) -> str:
        return self._source_type  # "hris", "idp", etc. — NOT "manual"

    async def detect(self) -> SourceIdentity | None:
        if not self._identity:
            return None
        return SourceIdentity(
            provider_type=self._source_type,
            identity=self._identity,
            account_id=self._account_id,
            display_name=self._display_name,
            raw={"attestation_type": "manual"},
        )


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_AUTO_PROVIDER_REGISTRY: dict[str, type[SourceProvider]] = {
    "git_repo": GitRepoProvider,
    "aws_identity": AWSIdentityProvider,
    "azure_identity": AzureIdentityProvider,
    "k8s_context": KubernetesContextProvider,
}

_AUTODETECT_TYPES: list[str] = list(_AUTO_PROVIDER_REGISTRY)


def resolve_providers(
    config_entries: list[dict[str, Any]] | None = None,
) -> list[SourceProvider]:
    """Build provider instances from config or fall back to auto-detect.

    When config_entries is None (no source_providers key in config),
    returns all four infra auto-detect providers for backward compat.
    """
    if config_entries is None:
        return [_AUTO_PROVIDER_REGISTRY[t]() for t in _AUTODETECT_TYPES]

    providers: list[SourceProvider] = []
    for entry in config_entries:
        if not entry.get("enabled", True):
            continue
        ptype = entry.get("type", "")
        if ptype == "manual":
            source_type = entry.get("source_type", "")
            identity = entry.get("identity", "")
            if not source_type or not identity:
                logger.warning(
                    "Manual provider missing source_type/identity, skipping: %r",
                    entry,
                )
                continue
            providers.append(
                ManualAttestationProvider(
                    source_type=source_type,
                    identity=identity,
                    display_name=entry.get("display_name", ""),
                    account_id=entry.get("account_id"),
                )
            )
        elif ptype in _AUTO_PROVIDER_REGISTRY:
            providers.append(_AUTO_PROVIDER_REGISTRY[ptype]())
        else:
            logger.warning("Unknown provider type in config: %s", ptype)
    return providers


# ---------------------------------------------------------------------------
# Provider orchestration
# ---------------------------------------------------------------------------


async def run_all_providers(
    providers: list[SourceProvider] | None = None,
) -> list[SourceIdentity]:
    """Run all providers in parallel, returning detected identities."""
    if providers is None:
        from pretorin.client.config import Config

        config = Config()
        providers = resolve_providers(config.source_providers)

    async def _safe_detect(provider: SourceProvider) -> SourceIdentity | None:
        try:
            return await asyncio.wait_for(provider.detect(), timeout=5)
        except Exception:
            logger.debug("Provider %s failed", provider.provider_type, exc_info=True)
            return None

    results = await asyncio.gather(*[_safe_detect(p) for p in providers])
    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------


def _snapshot_path(system_id: str, framework_id: str) -> Path:
    """Return the path for a scope-keyed snapshot file."""
    safe_system = system_id.replace("/", "_").replace("\\", "_")
    safe_framework = framework_id.replace("/", "_").replace("\\", "_")
    return SNAPSHOT_DIR / f"verified_context_{safe_system}_{safe_framework}.json"


def _source_to_dict(source: SourceIdentity) -> dict[str, Any]:
    """Serialize a SourceIdentity to a dict."""
    return {
        "provider_type": source.provider_type,
        "identity": source.identity,
        "account_id": source.account_id,
        "display_name": source.display_name,
        "raw": source.raw,
    }


def _source_from_dict(data: dict[str, Any]) -> SourceIdentity:
    """Deserialize a SourceIdentity from a dict."""
    return SourceIdentity(
        provider_type=data.get("provider_type", ""),
        identity=data.get("identity", ""),
        account_id=data.get("account_id"),
        display_name=data.get("display_name", ""),
        raw=data.get("raw", {}),
    )


def save_snapshot(snapshot: VerifiedSnapshot) -> None:
    """Persist a verified snapshot to disk."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(snapshot.system_id, snapshot.framework_id)
    data = {
        "system_id": snapshot.system_id,
        "framework_id": snapshot.framework_id,
        "api_base_url": snapshot.api_base_url,
        "sources": [_source_to_dict(s) for s in snapshot.sources],
        "verified_at": snapshot.verified_at,
        "ttl_seconds": snapshot.ttl_seconds,
        "status": snapshot.status.value,
        "cli_version": snapshot.cli_version,
    }
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o600)


def load_snapshot(system_id: str, framework_id: str) -> VerifiedSnapshot | None:
    """Load a verified snapshot from disk.

    Returns None if the file is missing, malformed, or has expired TTL.
    """
    path = _snapshot_path(system_id, framework_id)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    verified_at = data.get("verified_at", "")
    ttl_seconds = data.get("ttl_seconds", 3600)

    # Check TTL expiry
    try:
        verified_dt = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - verified_dt).total_seconds()
        if age > ttl_seconds:
            return None
    except (ValueError, TypeError):
        return None

    sources = tuple(_source_from_dict(s) for s in data.get("sources", []))
    try:
        status = VerificationStatus(data.get("status", "unverified"))
    except ValueError:
        status = VerificationStatus.UNVERIFIED

    return VerifiedSnapshot(
        system_id=data.get("system_id", ""),
        framework_id=data.get("framework_id", ""),
        api_base_url=data.get("api_base_url", ""),
        sources=sources,
        verified_at=verified_at,
        ttl_seconds=ttl_seconds,
        status=status,
        cli_version=data.get("cli_version", ""),
    )


def delete_snapshot(system_id: str, framework_id: str) -> bool:
    """Delete a snapshot file. Returns True if it existed."""
    path = _snapshot_path(system_id, framework_id)
    if path.exists():
        path.unlink()
        return True
    return False


def check_snapshot_validity(
    snapshot: VerifiedSnapshot,
    system_id: str,
    framework_id: str,
    api_base_url: str,
) -> VerificationStatus:
    """Check if a snapshot is still valid for the given context.

    Returns the snapshot's own status if everything matches,
    MISMATCH if scope or environment changed.
    """
    if snapshot.system_id != system_id or snapshot.framework_id != framework_id:
        return VerificationStatus.MISMATCH

    if snapshot.api_base_url.rstrip("/") != api_base_url.rstrip("/"):
        return VerificationStatus.MISMATCH

    return snapshot.status


def build_write_provenance(
    system_id: str,
    framework_id: str,
) -> dict[str, Any]:
    """Build a provenance dict for embedding in API write payloads.

    Returns a dict capturing the current verification state so artifacts
    record what sources were verified at write time. The dict is attached
    as ``_provenance`` in outgoing JSON; the platform silently ignores
    unknown fields until it adds schema support.

    When no snapshot exists, returns a minimal dict with
    ``verification_status: "unverified"``.
    """
    from pretorin import __version__

    snapshot = load_snapshot(system_id, framework_id)

    provenance: dict[str, Any] = {
        "cli_version": __version__,
        "source": "pretorin-cli",
    }

    if snapshot is None:
        provenance["verification_status"] = "unverified"
        return provenance

    from pretorin.client.config import Config

    config = Config()
    status = check_snapshot_validity(
        snapshot,
        system_id=system_id,
        framework_id=framework_id,
        api_base_url=config.platform_api_base_url,
    )
    provenance["verification_status"] = status.value
    provenance["verified_at"] = snapshot.verified_at
    provenance["verified_sources"] = [
        {
            "provider_type": s.provider_type,
            "identity": s.identity,
            **({"attestation_type": s.raw.get("attestation_type")} if s.raw.get("attestation_type") else {}),
        }
        for s in snapshot.sources
    ]
    return provenance
