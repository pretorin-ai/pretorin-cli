"""Verify extracted entities against actual platform state.

Three failure modes the cross-check protects against:

1. **Hallucinated entity** — control id that exists in no framework, system
   id the user has no access to. Hard error before workflow selection runs.
2. **Plausible-but-incoherent** — claimed framework doesn't match the
   system's active framework, claimed control ids exist in some framework
   but not the named one. Returns ambiguous to ask the user.
3. **Cross-system writes** — resolved system_id doesn't match the user's
   active CLI context. Returns ambiguous to confirm intent.

This module performs read-only platform calls. No LLM. The aim is to
catch wrong-framework / wrong-system writes *before* the agent starts
running.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.engagement.entities import EngagementEntities


@dataclass
class CrossCheckResult:
    """Outcome of validating entities against platform state.

    ``hard_errors`` are show-stoppers (hallucinated entities). The MCP
    handler converts them to MCP error responses. ``ambiguities`` are
    soft conflicts (wrong framework, cross-system) that the engagement
    layer surfaces as ``EngagementSelection(ambiguous=True, ...)``.
    """

    hard_errors: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)
    resolved_system_id: str | None = None
    resolved_framework_id: str | None = None

    @property
    def has_hard_error(self) -> bool:
        return bool(self.hard_errors)

    @property
    def has_ambiguity(self) -> bool:
        return bool(self.ambiguities)


async def cross_check_entities(
    client: PretorianClient,
    entities: EngagementEntities,
    *,
    active_system_id: str | None = None,
) -> CrossCheckResult:
    """Resolve entities against platform state and flag inconsistencies.

    ``active_system_id`` (from the user's CLI context) is used to detect
    cross-system writes. If the resolved system doesn't match the active
    one, that's an ambiguity (small extra friction; eliminates the silent-
    error class).
    """
    result = CrossCheckResult()

    # System resolution — accept either an id or a friendly name.
    if entities.system_id:
        resolved = await _resolve_system(client, entities.system_id)
        if resolved is None:
            result.hard_errors.append(
                f"System {entities.system_id!r} not found. Run pretorin_list_systems "
                "to see available systems, or check the user's spelling."
            )
        else:
            result.resolved_system_id = resolved
            if active_system_id and resolved != active_system_id:
                result.ambiguities.append(
                    f"Resolved system_id {resolved!r} does not match the active CLI "
                    f"context ({active_system_id!r}). Cross-system work needs explicit "
                    "confirmation — ask the user which system they meant."
                )

    # Framework resolution — must exist if named.
    if entities.framework_id:
        framework_ok = await _framework_exists(client, entities.framework_id)
        if not framework_ok:
            result.hard_errors.append(
                f"Framework {entities.framework_id!r} not found. Run "
                "pretorin_list_frameworks to see available frameworks."
            )
        else:
            result.resolved_framework_id = entities.framework_id

            # Coherence: if the system has a known active framework set,
            # warn when the named framework doesn't match.
            if result.resolved_system_id is not None:
                system_frameworks = await _system_active_frameworks(client, result.resolved_system_id)
                if system_frameworks and entities.framework_id not in system_frameworks:
                    result.ambiguities.append(
                        f"Framework {entities.framework_id!r} is not attached to system "
                        f"{result.resolved_system_id!r} (attached: {sorted(system_frameworks)}). "
                        "Confirm with the user before writing — wrong-framework writes are hard to undo."
                    )

    # Control coherence — every claimed control must exist somewhere, and
    # ideally in the claimed framework.
    if entities.control_ids:
        bad_controls: list[str] = []
        wrong_framework_controls: list[str] = []
        for control_id in entities.control_ids:
            scope = await _control_exists(
                client,
                control_id=control_id,
                framework_id=result.resolved_framework_id,
            )
            if scope == "missing":
                bad_controls.append(control_id)
            elif scope == "wrong_framework":
                wrong_framework_controls.append(control_id)
        if bad_controls:
            result.hard_errors.append(
                f"Control id(s) not found in any framework: {bad_controls}. "
                "Verify the user's spelling or framework choice."
            )
        if wrong_framework_controls:
            result.ambiguities.append(
                f"Control id(s) {wrong_framework_controls} exist in some framework but "
                f"not in {result.resolved_framework_id!r}. Confirm with the user "
                "which framework they meant."
            )

    return result


# ===========================================================================
# Helpers — narrow surface over the platform client.
# ===========================================================================


async def _resolve_system(client: PretorianClient, system_hint: str) -> str | None:
    """Return the canonical system_id matching ``system_hint`` (id or name)."""
    try:
        systems = await client.list_systems()
    except PretorianClientError:
        return None
    hint_lower = system_hint.lower()
    for s in systems:
        if s.get("id") == system_hint:
            return system_hint
        name = s.get("name", "")
        if name.lower() == hint_lower or name.lower().startswith(hint_lower):
            sid = s.get("id")
            if isinstance(sid, str):
                return sid
    return None


async def _framework_exists(client: PretorianClient, framework_id: str) -> bool:
    try:
        frameworks = await client.list_frameworks()
    except PretorianClientError:
        return False
    # FrameworkList may be a pydantic object or a dict-like; handle both.
    items: list[Any] = getattr(frameworks, "frameworks", None) or getattr(frameworks, "__root__", None) or []
    if not items and isinstance(frameworks, list):
        items = frameworks
    for f in items:
        fid = getattr(f, "id", None) if not isinstance(f, dict) else f.get("id")
        if fid == framework_id:
            return True
    return False


async def _system_active_frameworks(client: PretorianClient, system_id: str) -> set[str]:
    """Return the framework ids attached to ``system_id``.

    Empty set when the system doesn't carry framework metadata; in that
    case the coherence check is skipped (no signal, no warning).
    """
    try:
        status = await client.get_system_compliance_status(system_id)
    except PretorianClientError:
        return set()
    frameworks = status.get("frameworks") if isinstance(status, dict) else None
    if not isinstance(frameworks, list):
        return set()
    out: set[str] = set()
    for f in frameworks:
        if isinstance(f, dict):
            fid = f.get("framework_id") or f.get("id")
            if isinstance(fid, str):
                out.add(fid)
    return out


async def _control_exists(
    client: PretorianClient,
    *,
    control_id: str,
    framework_id: str | None,
) -> str:
    """Check whether ``control_id`` exists.

    Returns:
        "in_framework" — exists in the named framework (or any if framework_id is None).
        "wrong_framework" — exists somewhere but not in the named framework.
        "missing" — found in no framework.
    """
    if framework_id is not None:
        if await _control_in_framework(client, framework_id, control_id):
            return "in_framework"
        # Fall through — try any framework so we can distinguish missing
        # from wrong-framework.
    for fid in await _all_framework_ids(client):
        if framework_id is not None and fid == framework_id:
            continue
        if await _control_in_framework(client, fid, control_id):
            return "wrong_framework" if framework_id is not None else "in_framework"
    return "missing"


async def _control_in_framework(client: PretorianClient, framework_id: str, control_id: str) -> bool:
    try:
        await client.get_control(framework_id, control_id)
    except PretorianClientError:
        return False
    return True


async def _all_framework_ids(client: PretorianClient) -> list[str]:
    try:
        frameworks = await client.list_frameworks()
    except PretorianClientError:
        return []
    items: list[Any] = getattr(frameworks, "frameworks", None) or getattr(frameworks, "__root__", None) or []
    if not items and isinstance(frameworks, list):
        items = frameworks
    out: list[str] = []
    for f in items:
        fid = getattr(f, "id", None) if not isinstance(f, dict) else f.get("id")
        if isinstance(fid, str):
            out.append(fid)
    return out


__all__ = ["CrossCheckResult", "cross_check_entities"]
