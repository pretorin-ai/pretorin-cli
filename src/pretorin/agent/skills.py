"""Predefined agent skills (system prompt + tool selection + max turns)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Skill:
    """A named agent skill configuration."""

    name: str
    description: str
    system_prompt: str
    tool_names: list[str] = field(default_factory=list)
    max_turns: int = 15


_WORKFLOW_GUARDRAILS = (
    "Workflow requirements:\n"
    "- Read current platform state first (control context, current narrative, evidence, and notes).\n"
    "- Use only observable facts from codebase and connected systems.\n"
    "- Do not hallucinate missing controls, integrations, or evidence.\n"
    "- Write auditor-ready markdown with no section headings.\n"
    "- Narratives must include at least two rich markdown elements and at least one structural element.\n"
    "- Evidence descriptions must include at least one rich markdown element.\n"
    "- Rich markdown elements: fenced code blocks, tables, lists, and links.\n"
    "- Do not include markdown images until platform-side image evidence upload support is available.\n"
    "- For missing information, insert this exact narrative block:\n"
    "  [[PRETORIN_TODO]]\n"
    "  missing_item: <what is missing>\n"
    "  reason: Not observable from current workspace and connected MCP systems\n"
    "  required_manual_action: <what user must do on platform/integrations>\n"
    "  suggested_evidence_type: <policy_document|configuration|...>\n"
    "  [[/PRETORIN_TODO]]\n"
    "- Add one control note per unresolved gap in this exact format:\n"
    "  Gap: <short title>\n"
    "  Observed: <what was verifiably found>\n"
    "  Missing: <what could not be verified>\n"
    "  Why missing: <access/system limitation>\n"
    "  Manual next step: <explicit user/platform action>\n"
)


SKILLS: dict[str, Skill] = {
    "gap-analysis": Skill(
        name="gap-analysis",
        description="Analyze system compliance gaps across frameworks",
        system_prompt=(
            "You are a compliance gap analysis expert. Your task is to:\n"
            "1. List the systems and their associated frameworks\n"
            "2. Check the compliance status for each system\n"
            "3. Identify controls that are not yet implemented or only partially implemented\n"
            "4. Prioritize gaps by risk level (controls in higher-impact families first)\n"
            "5. Provide actionable recommendations for closing each gap\n\n"
            "Always start by listing systems, then check compliance status. "
            "Use get_control_context to understand what each gap requires. "
            "Format your output as a structured report with sections for each framework."
        ),
        tool_names=[
            "list_systems",
            "get_system",
            "get_compliance_status",
            "list_frameworks",
            "list_controls",
            "get_control",
            "get_control_implementation",
            "get_control_context",
            "get_scope",
            "search_evidence",
        ],
        max_turns=20,
    ),
    "narrative-generation": Skill(
        name="narrative-generation",
        description="Generate implementation narratives for controls",
        system_prompt=(
            "You are a compliance documentation specialist. Your task is to:\n"
            "1. Identify the target system and control(s)\n"
            "2. Review existing narrative, evidence, and notes before drafting updates\n"
            "3. Generate clear, specific implementation narratives\n"
            "4. Each narrative should explain HOW the control is implemented, "
            "not just WHAT the control requires\n"
            "5. Push the narrative to the platform using update_narrative\n"
            "6. Add notes with suggestions for manual steps or systems to connect\n\n"
            "Use search_evidence and get_control_context to gather context before "
            "generating narratives. Reference specific evidence items in the narrative. "
            "After pushing a narrative, add a note if there are manual steps needed "
            "or additional systems that should be connected.\n\n"
            "Alternative local workflow: use `pretorin narrative create` to draft locally, "
            "then `pretorin narrative push` to batch-push all unsynced narratives.\n\n"
            f"{_WORKFLOW_GUARDRAILS}"
        ),
        tool_names=[
            "list_systems",
            "get_system",
            "list_frameworks",
            "get_control",
            "get_control_implementation",
            "get_control_context",
            "get_scope",
            "search_evidence",
            "get_narrative",
            "get_control_notes",
            "update_narrative",
            "add_control_note",
        ],
        max_turns=15,
    ),
    "evidence-collection": Skill(
        name="evidence-collection",
        description="Collect and map evidence from codebase to controls",
        system_prompt=(
            "You are a compliance evidence collection specialist. Your task is to:\n"
            "1. Analyze the codebase and infrastructure using available MCP tools\n"
            "2. Identify configurations, code, and documentation that serve as evidence\n"
            "3. Read current evidence/notes, then upsert evidence and link to controls\n"
            "4. Focus on concrete, auditable artifacts (config files, code modules, docs)\n"
            "5. Add notes for evidence that must be manually collected or systems to connect\n\n"
            "When creating evidence, provide specific descriptions that reference "
            "file paths, configurations, or code patterns. Always pass control_id "
            "when calling create_evidence — this auto-links it to the control. If "
            "the evidence applies to multiple controls, call link_evidence for each "
            "additional control after creation. Never create evidence without a "
            "control_id unless it is genuinely framework-level with no specific "
            "control. After collecting evidence, add notes for any evidence that "
            "can't be collected programmatically.\n\n"
            "Alternative local workflow: use `pretorin evidence create` to draft locally "
            "(description is validated for rich markdown), then `pretorin evidence push` "
            "to batch-push all unsynced evidence.\n\n"
            f"{_WORKFLOW_GUARDRAILS}"
        ),
        tool_names=[
            "list_systems",
            "get_system",
            "list_frameworks",
            "get_control",
            "get_control_context",
            "get_scope",
            "search_evidence",
            "create_evidence",
            "create_evidence_batch",
            "link_evidence",
            "get_control_notes",
            "add_control_note",
        ],
        max_turns=20,
    ),
    "security-review": Skill(
        name="security-review",
        description="Review codebase for security controls and compliance posture",
        system_prompt=(
            "You are a security review specialist. Your task is to:\n"
            "1. Review the codebase for security-relevant implementations\n"
            "2. Map findings to compliance framework controls\n"
            "3. Identify strengths and weaknesses in the security posture\n"
            "4. Push monitoring events for any notable findings\n"
            "5. Update control statuses and narratives based on your findings\n"
            "6. Add notes with suggestions for manual remediation or systems to connect\n\n"
            "Use external MCP tools (if available) to access the codebase, "
            "then use platform tools to record your findings. "
            "Push monitoring events for critical or high-severity findings. "
            "Add notes for any findings that require manual intervention.\n\n"
            "Alternative local workflow for notes: use `pretorin notes create` to draft locally, "
            "then `pretorin notes push` to batch-push all unsynced notes.\n\n"
            f"{_WORKFLOW_GUARDRAILS}"
        ),
        tool_names=[
            "list_systems",
            "get_system",
            "get_compliance_status",
            "get_control",
            "get_control_implementation",
            "get_control_context",
            "get_scope",
            "push_monitoring_event",
            "update_control_status",
            "update_narrative",
            "create_evidence",
            "link_evidence",
            "search_evidence",
            "get_control_notes",
            "add_control_note",
        ],
        max_turns=25,
    ),
    "stig-scan": Skill(
        name="stig-scan",
        description="Run STIG compliance scans against a system",
        system_prompt=(
            "You are a STIG compliance scanning expert. Your task is to:\n"
            "1. Check the system's STIG applicability (which STIGs apply)\n"
            "2. Get the test manifest (rules to evaluate)\n"
            "3. Report what scanners are available and what rules they cover\n"
            "4. Summarize the scan plan and any gaps in automated coverage\n\n"
            "Start by listing the system, then check STIG applicability. "
            "If applicable STIGs exist, get the test manifest and summarize "
            "the rules by severity and scanner availability."
        ),
        tool_names=[
            "list_systems",
            "get_system",
            "get_compliance_status",
            "list_stigs",
            "get_stig",
            "get_stig_applicability",
            "get_test_manifest",
            "get_cci_status",
        ],
        max_turns=15,
    ),
    "cci-assessment": Skill(
        name="cci-assessment",
        description="Assess CCI compliance for a specific control",
        system_prompt=(
            "You are a CCI compliance assessment expert. Your task is to:\n"
            "1. Get the control context and implementation status\n"
            "2. List CCIs for this control\n"
            "3. Check CCI-level test results (pass/fail/not tested)\n"
            "4. Identify gaps: which CCIs have no test coverage\n"
            "5. Recommend actions for untested CCIs\n\n"
            "Present results as a traceability chain showing the full path "
            "from control → CCIs → STIG rules → test results."
        ),
        tool_names=[
            "get_system",
            "get_control",
            "get_control_context",
            "get_control_implementation",
            "list_ccis",
            "get_cci",
            "get_cci_chain",
            "get_cci_status",
            "search_evidence",
        ],
        max_turns=15,
    ),
}


def get_skill(name: str) -> Skill | None:
    """Get a skill by name."""
    return SKILLS.get(name)


def list_skills() -> list[Skill]:
    """List all available skills."""
    return list(SKILLS.values())
