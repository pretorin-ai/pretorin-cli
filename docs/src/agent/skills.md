# Agent Skills

Skills are predefined task templates that guide the agent through specific compliance workflows.

## Available Skills

| Skill | Description |
|-------|-------------|
| `gap-analysis` | Assess codebase against framework controls, identify gaps, and prioritize remediation |
| `narrative-generation` | Generate auditor-ready implementation narratives for controls |
| `evidence-collection` | Collect and map evidence from codebase to controls |
| `security-review` | Review codebase for security controls and compliance posture |

## Using Skills

```bash
# Gap analysis
pretorin agent run --skill gap-analysis "Analyze my system compliance gaps"

# Narrative generation
pretorin agent run --skill narrative-generation "Generate narratives for all AC controls"

# Evidence collection
pretorin agent run --skill evidence-collection "Collect evidence for AC-02 in this repo"

# Security review
pretorin agent run --skill security-review "Review this codebase for AC-02 coverage"
```

## List Skills

```bash
pretorin agent skills
```

## Skill Details

### Gap Analysis

Systematically assesses a codebase against a framework's controls. The agent:

1. Scopes the assessment to relevant control families
2. Prioritizes families with code evidence (Access Control, Audit, IA, SC, CM)
3. Searches the codebase for evidence matching AI guidance expectations
4. Assigns implementation status per control
5. Produces a report with findings and priority remediation items

See [Gap Analysis Workflow](../workflows/gap-analysis.md) for the detailed methodology.

### Narrative Generation

Generates control implementation narratives that meet auditor-readiness requirements:

- No markdown headings
- At least two rich markdown elements (code blocks, tables, lists, links)
- At least one structural element (code block, table, or list)
- TODO placeholders for missing information
- Only documents observable facts (no hallucination)

### Evidence Collection

Searches the codebase for evidence that maps to specific controls:

- Identifies relevant files and code patterns
- Creates evidence items with auditor-ready descriptions
- Links evidence to controls via the platform
- Flags gaps where evidence is missing

### Security Review

Reviews the codebase against specific controls:

- Analyzes code for control coverage
- Identifies implementation strengths and weaknesses
- Documents findings with file paths and line numbers
- Produces remediation recommendations
