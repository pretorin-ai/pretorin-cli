"""Server-side inspect — bundle platform read state into a single payload.

Called by ``pretorin_start_task`` to give the calling agent a fully-loaded
context plus the workflow recommendation in one round-trip.

Per the design WS0 §2b: pretorin runs the platform reads, no LLM here.
The result is a dict the calling agent inspects to render to the user
(when ``intent_verb=="inspect_status"``) or to inform follow-up work.

Failure mode: any one of the platform calls can fail (network, auth,
unsupported endpoint). Inspect is best-effort — failures are recorded
in the per-section ``error`` fields, the rest of the payload still
populates. The router doesn't depend on inspect succeeding.
"""

from __future__ import annotations

from typing import Any

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError


async def gather_inspect_summary(
    client: PretorianClient,
    *,
    system_id: str | None,
    framework_id: str | None,
) -> dict[str, Any]:
    """Run the inspect platform reads and return a structured summary.

    Sections always present (each with either data or an ``error`` string):

    - ``workflow_state`` — platform's per-system workflow stage rollup.
    - ``compliance_status`` — overall compliance posture.
    - ``pending_families`` — families with unfinished work.
    - ``pending_scope_questions`` — unanswered scope questions.
    - ``pending_policy_questions`` — unanswered policy questions.

    System-scoped sections are skipped (left empty) when ``system_id``
    is None; framework-scoped sections are skipped when ``framework_id``
    is None.
    """
    summary: dict[str, Any] = {}

    if system_id and framework_id:
        summary["workflow_state"] = await _safe_call(
            "workflow_state",
            client.get_workflow_state,
            system_id,
            framework_id,
        )
        summary["pending_families"] = await _safe_call(
            "pending_families",
            client.get_pending_families,
            system_id,
            framework_id,
        )
        summary["pending_scope_questions"] = await _safe_call(
            "pending_scope_questions",
            client.get_pending_scope_questions,
            system_id,
            framework_id,
        )
    else:
        summary["workflow_state"] = {"skipped": "needs system_id and framework_id"}
        summary["pending_families"] = {"skipped": "needs system_id and framework_id"}
        summary["pending_scope_questions"] = {"skipped": "needs system_id and framework_id"}

    if system_id:
        summary["compliance_status"] = await _safe_call(
            "compliance_status",
            client.get_system_compliance_status,
            system_id,
        )
    else:
        summary["compliance_status"] = {"skipped": "needs system_id"}

    # Policy questions are scoped per org-policy, not per system. We can't
    # enumerate them without a policy id, so we list the available
    # policies; the calling agent picks one in policy-question workflow.
    summary["org_policies"] = await _safe_call("org_policies", client.list_org_policies)
    summary["pending_policy_questions"] = []  # Populated only when a specific policy is named.

    return summary


async def _safe_call(label: str, fn: Any, *args: Any) -> Any:
    """Call ``fn(*args)``; on PretorianClientError, return ``{"error": msg}``.

    Inspect is best-effort. The router never depends on a successful
    inspect — it only depends on the entities and a few specific keys
    (``pending_scope_questions``, ``pending_policy_questions``) which
    are surfaced as empty lists when missing.
    """
    try:
        return await fn(*args)
    except PretorianClientError as exc:
        return {"error": str(exc), "section": label}
    except Exception as exc:  # noqa: BLE001 — last-resort safety
        return {"error": f"unexpected error in {label}: {exc}", "section": label}


__all__ = ["gather_inspect_summary"]
