"""Engagement layer — pretorin's routing boundary.

The first thing a calling agent does when the user says "work on AC-2"
or "answer my scope questionnaire" or "draft narratives for the AC family"
is call ``pretorin_start_task``. The agent supplies structured entities
it extracted from the user prompt (its own LLM does the parsing) and
pretorin applies deterministic Python rules to pick a workflow.

Three layers of separation make this trustworthy:

1. **Entity extraction** happens in the calling agent's LLM (it's the one
   with the prompt). Pretorin doesn't run an LLM here.
2. **Cross-check** in pretorin verifies entities are coherent against
   platform state — hallucinated control ids fail loud, plausible-but-
   incoherent claims (wrong framework, wrong system) return ambiguous.
3. **Workflow selection** is a pure-Python rule cascade over the
   cross-checked entities + the inspect summary. No agent reasoning.

Drift is impossible by construction: the rule either matched or didn't.

Per the recipe-implementation design's WS0 (5-7 days). The router lands
on top of the WS5 substrate (workflow registry + 4 playbooks) so the
``selected_workflow`` field has somewhere to point.
"""

from __future__ import annotations

from pretorin.engagement.entities import EngagementEntities
from pretorin.engagement.rules import select_workflow
from pretorin.engagement.selection import EngagementSelection

__all__ = [
    "EngagementEntities",
    "EngagementSelection",
    "select_workflow",
]
