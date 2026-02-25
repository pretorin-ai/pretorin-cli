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
            "list_systems", "get_system", "get_compliance_status",
            "list_frameworks", "get_control", "get_control_implementation",
            "get_control_context", "get_scope", "search_evidence",
        ],
        max_turns=20,
    ),
    "narrative-generation": Skill(
        name="narrative-generation",
        description="Generate implementation narratives for controls",
        system_prompt=(
            "You are a compliance documentation specialist. Your task is to:\n"
            "1. Identify the target system and control(s)\n"
            "2. Review existing evidence and implementation details using get_control_context\n"
            "3. Generate clear, specific implementation narratives\n"
            "4. Each narrative should explain HOW the control is implemented, "
            "not just WHAT the control requires\n"
            "5. Push the narrative to the platform using update_narrative\n\n"
            "Use search_evidence and get_control_context to gather context before "
            "generating narratives. Reference specific evidence items in the narrative."
        ),
        tool_names=[
            "list_systems", "get_system", "get_control",
            "get_control_implementation", "get_control_context", "get_scope",
            "search_evidence", "generate_narrative", "get_narrative",
            "update_narrative",
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
            "3. Create evidence items on the platform and link them to controls\n"
            "4. Focus on concrete, auditable artifacts (config files, code modules, docs)\n\n"
            "When creating evidence, provide specific descriptions that reference "
            "file paths, configurations, or code patterns. Link each evidence item "
            "to the most relevant control(s)."
        ),
        tool_names=[
            "list_systems", "get_system", "list_frameworks", "get_control",
            "get_control_context", "get_scope",
            "search_evidence", "create_evidence",
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
            "5. Update control statuses and narratives based on your findings\n\n"
            "Use external MCP tools (if available) to access the codebase, "
            "then use platform tools to record your findings. "
            "Push monitoring events for critical or high-severity findings."
        ),
        tool_names=[
            "list_systems", "get_system", "get_compliance_status",
            "get_control", "get_control_implementation",
            "get_control_context", "get_scope",
            "push_monitoring_event", "update_control_status",
            "update_narrative", "create_evidence", "search_evidence",
        ],
        max_turns=25,
    ),
}


def get_skill(name: str) -> Skill | None:
    """Get a skill by name."""
    return SKILLS.get(name)


def list_skills() -> list[Skill]:
    """List all available skills."""
    return list(SKILLS.values())
