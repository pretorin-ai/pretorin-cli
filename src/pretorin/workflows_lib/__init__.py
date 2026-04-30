"""Workflow registry — calling-agent playbooks.

Workflows sit one layer above recipes in the three-layer routing model
(engagement → workflow → recipe). Each workflow is a markdown file at
``src/pretorin/workflows_lib/_workflows/<id>/workflow.md`` with YAML
frontmatter and a body. The body is the playbook the calling agent reads
to know how to iterate items in that workflow's domain (one control,
one scope question, the whole campaign, etc.).

Workflows do NOT contain Python scripts and do NOT execute server-side.
They're prompts for the calling agent. The agent reads the body, follows
the iteration pattern described in it, and picks recipes per item from
the recipe registry (``pretorin.recipes``).

The legacy ``pretorin.workflows`` package contains the *implementation*
of workflows (campaign iteration loop, ai_generation, evidence
validation, etc.). That code stays where it is. ``workflows_lib`` is
purely the prompt-surface registry.

Per RFC 0001 v0.5 §"Three-layer routing" and the recipe-implementation
design's WS5.
"""

from __future__ import annotations

__all__: list[str] = []
