"""MCP handlers for workflow-playbook discovery (the workflows_lib registry).

Disambiguation: this is **not** the legacy ``handlers/workflow.py`` (which
covers the platform's workflow-state surface — campaign, scope/policy
questionnaires). This module exposes the new ``workflows_lib/`` registry of
calling-agent playbooks (single-control, scope-question, policy-question,
campaign) — markdown bodies the calling agent reads to know how to iterate
items in a domain.

Per the design WS5 §"Shared mechanism": workflows sit one layer above
recipes. The agent picks a workflow first (engagement-layer routing in WS0,
or directly via ``pretorin_list_workflows``), reads the playbook, then picks
recipes per-item from the recipe registry.

Tools:
- ``pretorin_list_workflows`` enumerates loaded workflow playbooks.
- ``pretorin_get_workflow`` returns one workflow's full manifest and body.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import format_error, format_json, require, safe_args
from pretorin.workflows_lib.registry import get_workflow as registry_get_workflow
from pretorin.workflows_lib.registry import load_all as registry_load_all

logger = logging.getLogger(__name__)


async def handle_list_workflows(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Enumerate loaded workflow playbooks.

    Optional filter: ``iterates_over`` narrows to one item-iteration shape
    (``single_control`` / ``scope_questions`` / ``policy_questions`` /
    ``campaign_items``). Returns summary dicts (id, name, description,
    use_when, produces, iterates_over, recipes_commonly_used) so the agent
    can scan the menu without pulling each body.

    Body is intentionally NOT included — call ``pretorin_get_workflow`` once
    the agent has narrowed the candidate.
    """
    logger.debug("handle_list_workflows called with %s", safe_args(arguments))
    iterates_filter = arguments.get("iterates_over")

    workflows = registry_load_all()
    if iterates_filter:
        workflows = [w for w in workflows if w.manifest.iterates_over == iterates_filter]

    return format_json(
        {
            "total": len(workflows),
            "workflows": [
                {
                    "id": w.manifest.id,
                    "name": w.manifest.name,
                    "version": w.manifest.version,
                    "description": w.manifest.description,
                    "use_when": w.manifest.use_when,
                    "produces": w.manifest.produces,
                    "iterates_over": w.manifest.iterates_over,
                    "recipes_commonly_used": list(w.manifest.recipes_commonly_used),
                }
                for w in workflows
            ],
        }
    )


async def handle_get_workflow_lib(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Return one workflow's full manifest and body.

    Named ``handle_get_workflow_lib`` (not ``handle_get_workflow``) because
    ``handlers/workflow.py`` already exposes ``handle_get_workflow_state``;
    keeping the two namespaces disjoint avoids future grep confusion.
    """
    logger.debug("handle_get_workflow_lib called with %s", safe_args(arguments))
    err = require(arguments, "workflow_id")
    if err:
        return format_error(err)

    workflow_id = str(arguments["workflow_id"])
    loaded = registry_get_workflow(workflow_id)
    if loaded is None:
        return format_error(f"No workflow found with id {workflow_id!r}")

    return format_json(
        {
            "id": loaded.manifest.id,
            "manifest": loaded.manifest.model_dump(),
            "body": loaded.body,
        }
    )
