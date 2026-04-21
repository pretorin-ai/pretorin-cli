"""Source attestation: models, providers, snapshot persistence, and manifest evaluation.

Verifies that the CLI session is connected to the expected external sources
(git repo, cloud account, k8s cluster) before allowing compliance writes.
Phase 1 detects session drift; Phase 3 adds correctness checking via source manifests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
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
    source_role: str = ""
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
# Source manifest models (Phase 3)
# ---------------------------------------------------------------------------


class SourceLevel(str, Enum):
    """Requirement level for a source in a manifest."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class SourceRequirement:
    """Single expected source declared in a manifest."""

    source_type: str
    level: SourceLevel
    identity_pattern: str | None = None
    account_id: str | None = None
    description: str = ""


@dataclass(frozen=True)
class SourceManifest:
    """Declarative manifest of expected sources for a system."""

    version: str
    system_sources: tuple[SourceRequirement, ...] = ()
    family_sources: dict[str, tuple[SourceRequirement, ...]] = field(default_factory=dict)
    workflow_sources: dict[str, tuple[SourceRequirement, ...]] = field(default_factory=dict)


class ManifestStatus(str, Enum):
    """Result of evaluating a manifest against detected sources."""

    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    PARTIAL = "partial"
    NO_MANIFEST = "no_manifest"


@dataclass(frozen=True)
class ManifestResult:
    """Outcome of evaluating a manifest against detected sources."""

    status: ManifestStatus
    satisfied: tuple[SourceRequirement, ...] = ()
    missing_required: tuple[SourceRequirement, ...] = ()
    missing_recommended: tuple[SourceRequirement, ...] = ()
    warnings: tuple[str, ...] = ()


# 800-171r3 numeric family prefix -> NIST 800-53 family abbreviation
_FAMILY_MAP_171: dict[str, str] = {
    "03": "ac",
    "04": "at",
    "05": "au",
    "06": "cm",
    "07": "ia",
    "08": "ir",
    "09": "ma",
    "10": "mp",
    "11": "pe",
    "12": "ps",
    "13": "ra",
    "14": "ca",
    "15": "pl",
    "16": "pm",
    "17": "sc",
    "18": "si",
    "19": "sr",
}

# Module-level caches and constants
_git_root_cache: Path | None = None
_git_root_checked: bool = False
_MANIFEST_LOAD_CACHE: dict[str, SourceManifest] = {}  # keyed by system_id
_LEVEL_RANK: dict[SourceLevel, int] = {
    SourceLevel.REQUIRED: 0,
    SourceLevel.RECOMMENDED: 1,
    SourceLevel.OPTIONAL: 2,
}


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
            source_role="code",
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
            source_role="identity",
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
            source_role="identity",
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
            source_role="deployment",
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
        source_role: str = "monitoring",
    ) -> None:
        self._source_type = source_type
        self._identity = identity
        self._display_name = display_name or identity
        self._account_id = account_id
        self._source_role = source_role

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
            source_role=self._source_role,
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
                    source_role=entry.get("source_role", "monitoring"),
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


# ---------------------------------------------------------------------------
# Source manifest loading and evaluation (Phase 3)
# ---------------------------------------------------------------------------


def _requirement_from_dict(data: dict[str, Any]) -> SourceRequirement | None:
    """Deserialize a single requirement from manifest JSON.

    Returns None and logs a warning for invalid entries.
    """
    source_type = data.get("source_type", "")
    if not source_type:
        logger.warning("Manifest entry missing source_type, skipping: %r", data)
        return None

    raw_level = data.get("level", "")
    try:
        level = SourceLevel(raw_level)
    except ValueError:
        logger.warning("Unknown manifest level %r for source_type %r, skipping", raw_level, source_type)
        return None

    return SourceRequirement(
        source_type=source_type,
        level=level,
        identity_pattern=data.get("identity_pattern"),
        account_id=data.get("account_id"),
        description=data.get("description", ""),
    )


def _parse_manifest(data: dict[str, Any]) -> SourceManifest | None:
    """Parse a manifest dict into a SourceManifest.

    Returns None if the manifest is missing the required ``version`` key.
    Individual malformed entries are warned and skipped.
    """
    version = data.get("version")
    if not version:
        logger.warning("Source manifest missing 'version' key, ignoring")
        return None

    if str(version) != "1":
        logger.warning("Unsupported manifest version %r (expected '1'), ignoring", version)
        return None

    system_reqs: list[SourceRequirement] = []
    for entry in data.get("system_sources", []):
        req = _requirement_from_dict(entry)
        if req is not None:
            system_reqs.append(req)

    family_reqs: dict[str, tuple[SourceRequirement, ...]] = {}
    for family_key, entries in data.get("family_sources", {}).items():
        parsed = [r for e in entries if (r := _requirement_from_dict(e)) is not None]
        if parsed:
            family_reqs[family_key.lower()] = tuple(parsed)

    workflow_reqs: dict[str, tuple[SourceRequirement, ...]] = {}
    for wf_key, entries in data.get("workflow_sources", {}).items():
        parsed = [r for e in entries if (r := _requirement_from_dict(e)) is not None]
        if parsed:
            workflow_reqs[wf_key] = tuple(parsed)

    return SourceManifest(
        version=str(version),
        system_sources=tuple(system_reqs),
        family_sources=family_reqs,
        workflow_sources=workflow_reqs,
    )


def _get_git_root() -> Path | None:
    """Return the git repository root, cached across calls."""
    global _git_root_cache, _git_root_checked  # noqa: PLW0603
    if _git_root_checked:
        return _git_root_cache
    _git_root_checked = True
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            _git_root_cache = Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return _git_root_cache


def load_manifest(system_id: str, *, use_cache: bool = True) -> SourceManifest | None:
    """Resolve a source manifest from the layered config sources.

    Precedence:
    1. ``PRETORIN_SOURCE_MANIFEST`` env var (JSON string or file path)
    2. ``.pretorin/source-manifest.json`` in the git repo root
    3. ``~/.pretorin/source-manifest-{system_id}.json``
    4. ``source_manifest`` key in ``~/.pretorin/config.json``

    Returns ``None`` when no manifest is found. Results are cached per
    ``system_id`` to avoid repeated file I/O within a single process.
    """
    if use_cache:
        cached = _MANIFEST_LOAD_CACHE.get(system_id)
        if cached is not None:
            return cached

    import os

    resolved: SourceManifest | None = None

    # 1. Environment variable
    env_val = os.environ.get("PRETORIN_SOURCE_MANIFEST", "")
    if env_val:
        try:
            resolved = _parse_manifest(json.loads(env_val))
        except json.JSONDecodeError:
            env_path = Path(env_val)
            if env_path.is_file():
                try:
                    resolved = _parse_manifest(json.loads(env_path.read_text()))
                except (json.JSONDecodeError, OSError):
                    logger.warning("Failed to read manifest from %s", env_path)

    # 2. Repo-local .pretorin/source-manifest.json
    if resolved is None:
        git_root = _get_git_root()
        if git_root is not None:
            repo_path = git_root / ".pretorin" / "source-manifest.json"
            if repo_path.is_file():
                try:
                    resolved = _parse_manifest(json.loads(repo_path.read_text()))
                except (json.JSONDecodeError, OSError):
                    logger.warning("Failed to read manifest from %s", repo_path)

    # 3. User config: ~/.pretorin/source-manifest-{system_id}.json
    if resolved is None:
        safe_system = system_id.replace("/", "_").replace("\\", "_")
        user_path = CONFIG_DIR / f"source-manifest-{safe_system}.json"
        if user_path.is_file():
            try:
                resolved = _parse_manifest(json.loads(user_path.read_text()))
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to read manifest from %s", user_path)

    # 4. Inline config key
    if resolved is None:
        from pretorin.client.config import Config

        inline = Config().source_manifest
        if inline and isinstance(inline, dict):
            resolved = _parse_manifest(inline)

    if resolved is not None:
        _MANIFEST_LOAD_CACHE[system_id] = resolved
    return resolved


def _matches_requirement(source: SourceIdentity, req: SourceRequirement) -> bool:
    """Check if a detected source satisfies a manifest requirement.

    Matching rules:
    - ``source_type`` must match exactly.
    - If ``identity_pattern`` is set, the source identity must either equal
      the pattern or start with ``pattern + '/'`` (anchored segment match).
    - If ``account_id`` is set, it must match exactly.
    """
    if source.provider_type != req.source_type:
        return False

    if req.identity_pattern is not None:
        pattern = req.identity_pattern
        if source.identity != pattern and not source.identity.startswith(pattern + "/"):
            return False

    if req.account_id is not None:
        if source.account_id != req.account_id:
            return False

    return True


def _collect_requirements(
    manifest: SourceManifest,
    family_id: str | None = None,
) -> list[SourceRequirement]:
    """Merge system-level and family-level requirements.

    When the same ``source_type`` appears at both levels, the stricter
    level wins (REQUIRED > RECOMMENDED > OPTIONAL).
    """
    # Start with system-level requirements keyed by source_type
    by_type: dict[str, SourceRequirement] = {}
    for req in manifest.system_sources:
        existing = by_type.get(req.source_type)
        if existing is None or _LEVEL_RANK[req.level] < _LEVEL_RANK[existing.level]:
            by_type[req.source_type] = req

    # Merge family-level requirements
    if family_id and family_id in manifest.family_sources:
        for req in manifest.family_sources[family_id]:
            existing = by_type.get(req.source_type)
            if existing is None or _LEVEL_RANK[req.level] < _LEVEL_RANK[existing.level]:
                by_type[req.source_type] = req

    return list(by_type.values())


def evaluate_manifest(
    manifest: SourceManifest,
    sources: tuple[SourceIdentity, ...],
    family_id: str | None = None,
) -> ManifestResult:
    """Evaluate detected sources against manifest requirements.

    Returns a ``ManifestResult`` with the overall status and categorized
    requirements.
    """
    requirements = _collect_requirements(manifest, family_id=family_id)
    if not requirements:
        return ManifestResult(status=ManifestStatus.SATISFIED)

    satisfied: list[SourceRequirement] = []
    missing_required: list[SourceRequirement] = []
    missing_recommended: list[SourceRequirement] = []

    for req in requirements:
        matched = any(_matches_requirement(src, req) for src in sources)
        if matched:
            satisfied.append(req)
        elif req.level == SourceLevel.REQUIRED:
            missing_required.append(req)
        elif req.level == SourceLevel.RECOMMENDED:
            missing_recommended.append(req)
        # Optional missing sources are not tracked

    if missing_required:
        status = ManifestStatus.UNSATISFIED
    elif missing_recommended:
        status = ManifestStatus.PARTIAL
    else:
        status = ManifestStatus.SATISFIED

    return ManifestResult(
        status=status,
        satisfied=tuple(satisfied),
        missing_required=tuple(missing_required),
        missing_recommended=tuple(missing_recommended),
    )


def extract_family_from_control_id(control_id: str) -> str | None:
    """Extract the 2-letter control family prefix from a control ID.

    Supports three formats:
    - NIST 800-53: ``ac-02`` -> ``"ac"``
    - CMMC: ``AC.L2-3.1.1`` -> ``"ac"``
    - 800-171r3: ``03.01.01`` -> ``"ac"`` (via ``_FAMILY_MAP_171``)

    Returns ``None`` for unrecognized formats.
    """
    if not control_id:
        return None

    stripped = control_id.strip()

    # NIST 800-53: ac-02, SC-07, ac-02.1
    match = re.match(r"^([a-zA-Z]{2})-", stripped)
    if match:
        return match.group(1).lower()

    # CMMC: AC.L2-3.1.1, AC.L1-3.1.1
    match = re.match(r"^([a-zA-Z]{2})\.", stripped)
    if match:
        return match.group(1).lower()

    # 800-171r3: 03.01.01 (numeric prefix mapped via _FAMILY_MAP_171)
    match = re.match(r"^(\d{2})\.\d{2}\.\d{2}", stripped)
    if match:
        return _FAMILY_MAP_171.get(match.group(1))

    return None


def build_write_provenance(
    system_id: str,
    framework_id: str,
    *,
    control_id: str | None = None,
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

    # Manifest evaluation (load_manifest handles its own caching)
    manifest = load_manifest(system_id)

    if manifest is not None:
        family = extract_family_from_control_id(control_id) if control_id else None
        result = evaluate_manifest(manifest, snapshot.sources, family_id=family)
        provenance["manifest_status"] = result.status.value
        if result.missing_required:
            provenance["missing_required_sources"] = [r.source_type for r in result.missing_required]
    else:
        provenance["manifest_status"] = ManifestStatus.NO_MANIFEST.value

    return provenance


# ---------------------------------------------------------------------------
# Source verification mapping (platform SourceVerificationPayload shape)
# ---------------------------------------------------------------------------

# Maps CLI provider_type to platform CanonicalSourceType enum values.
# Translation happens at serialization time — SourceIdentity.provider_type is unchanged.
PROVIDER_TO_CANONICAL_SOURCE_TYPE: dict[str, str] = {
    "git_repo": "github_repo",
    "aws_identity": "aws_account",
    "azure_identity": "entra_tenant",
    "k8s_context": "kubernetes_cluster",
}


def build_source_verification(
    system_id: str,
    framework_id: str,
) -> dict[str, Any] | None:
    """Build a platform-compatible source verification payload.

    Returns None if no snapshot exists or session is unverified.
    The returned dict matches the platform's SourceVerificationPayload schema.
    """
    snapshot = load_snapshot(system_id, framework_id)
    if snapshot is None:
        return None

    from pretorin.client.config import Config

    config = Config()
    status = check_snapshot_validity(
        snapshot,
        system_id=system_id,
        framework_id=framework_id,
        api_base_url=config.platform_api_base_url,
    )

    if status == VerificationStatus.UNVERIFIED:
        return None

    sources = []
    for s in snapshot.sources:
        canonical_type = PROVIDER_TO_CANONICAL_SOURCE_TYPE.get(s.provider_type, "custom")
        role = s.source_role or "monitoring"
        sources.append(
            {
                "source_type": canonical_type,
                "source_role": role,
                "identifier": s.identity,
                "verified": status == VerificationStatus.VERIFIED,
                "verified_at": snapshot.verified_at,
            }
        )

    return {
        "overall_state": status.value,
        "verified_at": snapshot.verified_at,
        "ttl_seconds": 3600,
        "sources": sources,
    }


def extract_git_context_from_snapshot(
    system_id: str,
    framework_id: str,
) -> dict[str, str] | None:
    """Extract git repo URL and commit hash from the attested snapshot.

    Returns a dict with code_repository and code_commit_hash, or None
    if no snapshot or no git provider in the snapshot.
    """
    snapshot = load_snapshot(system_id, framework_id)
    if snapshot is None:
        return None

    for s in snapshot.sources:
        if s.provider_type == "git_repo":
            result: dict[str, str] = {}
            if s.identity:
                result["code_repository"] = s.identity
            commit = s.raw.get("head_commit", "")
            if commit:
                result["code_commit_hash"] = commit
            return result if result else None

    return None
