"""Pydantic models for Pretorin API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict

# =============================================================================
# Framework Models
# =============================================================================


class FrameworkSummary(BaseModel):
    """Summary information about a framework."""

    id: str
    external_id: str
    title: str
    version: str
    description: str | None = None
    tier: str | None = None
    category: str | None = None
    catalog_format: str | None = None
    families_count: int = 0
    controls_count: int = 0


class FrameworkList(BaseModel):
    """List of available frameworks."""

    frameworks: list[FrameworkSummary]
    total: int


class FrameworkMetadata(BaseModel):
    """Detailed framework metadata."""

    id: str
    external_id: str
    title: str
    version: str
    oscal_version: str | None = Field(default=None, alias="oscal-version")
    last_modified: str | None = Field(default=None, alias="last-modified")
    published: str | None = None
    description: str | None = None
    tier: str | None = None
    category: str | None = None
    catalog_format: str | None = None
    ai_context: dict[str, Any] | None = None


# =============================================================================
# Control Family Models
# =============================================================================


class ControlFamilySummary(BaseModel):
    """Summary of a control family."""

    id: str
    title: str
    class_type: str | None = Field(default=None, alias="class")
    controls_count: int = 0
    ai_context: dict[str, Any] | None = None


class ControlInFamily(BaseModel):
    """Control summary within a family."""

    id: str
    title: str
    class_type: str | None = Field(default=None, alias="class")


class ControlFamilyDetail(BaseModel):
    """Detailed control family information."""

    id: str
    title: str
    class_type: str = Field(alias="class")
    controls: list[ControlInFamily] = Field(default_factory=list)
    ai_context: dict[str, Any] | None = None


# =============================================================================
# Control Models
# =============================================================================


class ControlSummary(BaseModel):
    """Summary of a control."""

    id: str
    title: str
    family_id: str


class ControlDetail(BaseModel):
    """Detailed control information."""

    id: str
    title: str
    class_type: str | None = Field(default=None, alias="class")
    control_type: str | None = None  # organizational, system, or hybrid
    props: list[dict[str, Any]] | None = None
    params: list[dict[str, Any]] | None = None
    parts: list[dict[str, Any]] | None = None
    controls: list[dict[str, Any]] | None = None  # control enhancements
    ai_guidance: dict[str, Any] | None = None


class ControlMetadata(BaseModel):
    """Control metadata for display."""

    title: str
    family: str
    type: str  # organizational, system, or hybrid


class RelatedControl(BaseModel):
    """Related control summary."""

    id: str
    title: str
    family_id: str


class ControlReferences(BaseModel):
    """Reference data for a control."""

    control_id: str
    title: str | None = None
    statement: str | None = None
    guidance: str | None = None
    objectives: list[str] = Field(default_factory=list)
    parameters: list[dict[str, Any]] | None = None
    related_controls: list[RelatedControl] = Field(default_factory=list)


class ControlBatchItem(BaseModel):
    """Detailed control data returned from the batch controls endpoint."""

    id: str
    title: str
    family_id: str
    control_type: str | None = None
    statement: str | None = None
    guidance: str | None = None
    objectives: list[str] = Field(default_factory=list)
    parameters: list[dict[str, Any]] | None = None
    ai_guidance: dict[str, Any] | None = None


class ControlBatchResponse(BaseModel):
    """Batch response for one-framework control retrieval."""

    controls: list[ControlBatchItem] = Field(default_factory=list)
    total: int = 0


# =============================================================================
# Document Requirement Models
# =============================================================================


class DocumentRequirement(BaseModel):
    """Document requirement for a framework."""

    id: str
    document_name: str
    description: str | None = None
    requirement_type: str  # explicit or implicit
    is_required: bool
    control_references: list[str] | None = None
    format_guidance: str | None = None


class DocumentRequirementList(BaseModel):
    """List of document requirements for a framework."""

    framework_id: str
    framework_title: str
    explicit_documents: list[DocumentRequirement] = Field(default_factory=list)
    implicit_documents: list[DocumentRequirement] = Field(default_factory=list)
    total: int = 0


# =============================================================================
# Compliance Artifact Models (for Analysis Feature)
# =============================================================================


class Evidence(BaseModel):
    """Evidence supporting a control implementation."""

    description: str = Field(..., description="Narrative evidence statement")
    file_path: str | None = Field(default=None, description="Path to file containing evidence")
    line_numbers: str | None = Field(default=None, description="Line range (e.g., '10-25')")
    code_snippet: str | None = Field(default=None, description="Relevant code excerpt")


class ImplementationStatement(BaseModel):
    """Implementation statement for a specific control."""

    control_id: str = Field(..., description="Control ID (e.g., ac-02, au-02)")
    description: str = Field(
        ...,
        description="2-3 sentence narrative of how control is implemented",
    )
    implementation_status: Literal["implemented", "partial", "planned", "not-applicable"] = Field(
        ...,
        description="Current implementation status",
    )
    responsible_roles: list[str] = Field(
        default=["System Administrator"],
        description="Roles responsible for this control",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence supporting this implementation",
    )
    remarks: str | None = Field(default=None, description="Additional notes")


class ComponentDefinition(BaseModel):
    """Definition of a system component for compliance."""

    component_id: str = Field(
        ...,
        description="Source identifier (e.g., repository name, system ID)",
    )
    title: str = Field(..., description="Component name")
    description: str = Field(..., description="What this component does")
    type: Literal["software", "hardware", "service", "policy", "process"] = Field(
        default="software",
        description="Component type",
    )
    control_implementations: list[ImplementationStatement] = Field(
        default_factory=list,
        description="Control implementations for this component",
    )


class ComplianceArtifact(BaseModel):
    """A compliance artifact containing implementation evidence for a control."""

    framework_id: str = Field(..., description="Framework ID (e.g., fedramp-moderate)")
    control_id: str = Field(..., description="Control ID (e.g., ac-02)")
    component: ComponentDefinition = Field(..., description="Component definition")
    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Confidence level in the analysis",
    )


class ArtifactValidationResult(BaseModel):
    """Result of artifact validation."""

    valid: bool = Field(..., description="Whether the artifact is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


# =============================================================================
# System Models
# =============================================================================


class SystemDetail(BaseModel):
    """Detailed system information."""

    id: str
    name: str
    description: str | None = None
    frameworks: list[dict[str, Any]] = Field(default_factory=list)
    security_impact_level: str | None = None


# =============================================================================
# Evidence Models (Platform)
# =============================================================================


class EvidenceItemResponse(BaseModel):
    """Evidence item from the platform."""

    id: str
    name: str
    description: str | None = None
    evidence_type: str | None = None
    status: str | None = None
    control_mappings: list[dict[str, Any]] = Field(default_factory=list)
    collected_at: str | None = None


class EvidenceCodeContext(TypedDict, total=False):
    """Typed dict for code provenance fields passed through evidence creation."""

    code_file_path: str
    code_line_numbers: str
    code_snippet: str
    code_repository: str
    code_commit_hash: str


# =============================================================================
# Audit-Trail Metadata (recipe-implementation WS1a)
#
# Per the draft RFC at docs/rfcs/draft-evidence-metadata.md.
#
# During WS1a/b (the migration window) audit_metadata is sent as an OPTIONAL field
# on EvidenceCreate / EvidenceBatchItemCreate. The platform tolerates its absence.
# WS1c flips the field to required once platform-side fields land.
#
# The recipe execution context (WS2) stamps producer_kind="recipe" + producer_id
# + producer_version automatically; manual CLI writes auto-stamp producer_kind="cli"
# via the build_*_metadata helpers in pretorin.evidence.audit_metadata.
# =============================================================================


SourceType = Literal[
    "code_snippet",
    "log_excerpt",
    "configuration",
    "screenshot",
    "document",
    "attestation",
    "scan_result",
]
"""Evidence source-type enum per draft RFC §3 ('source_type')."""


class RedactionSummary(BaseModel):
    """Top-level schema'd redaction counts (draft RFC §6, recommendation).

    Per-recipe granularity goes in `details`. The schema'd counts let the platform
    render a consistent badge; `details` preserves recipe-level granularity for
    downstream tooling.
    """

    secrets: int = Field(default=0, ge=0, description="Secret-pattern redactions (API keys, passwords, tokens)")
    pii: int = Field(default=0, ge=0, description="PII redactions")
    custom: int = Field(default=0, ge=0, description="Recipe-defined redactions outside the above categories")
    details: dict[str, int] | None = Field(
        default=None,
        description="Optional per-recipe granular counts, e.g. {aws_keys: 2, github_pats: 1}",
    )


class EvidenceAuditMetadata(BaseModel):
    """Audit-trail metadata stamped on every evidence/narrative write.

    Required minimum (per draft RFC §'Required vs optional'): producer_kind,
    producer_id, captured_at, source_type, source_uri, content_hash. Other fields
    are strongly encouraged but pydantic-optional.

    Drift-prevention rationale: every CLI/agent/recipe write path produces an
    instance of this model via build_cli_metadata / build_agent_metadata /
    build_recipe_metadata helpers in pretorin.evidence.audit_metadata. Single
    construction surface; no path stamps fields on its own.
    """

    producer_kind: Literal["cli", "recipe", "agent", "manual_upload", "api"] = Field(
        ..., description="Who or what created this record"
    )
    producer_id: str = Field(..., min_length=1, description="Producer identifier (recipe id, agent id, 'cli', etc.)")
    producer_version: str | None = Field(
        default=None,
        description="Producer version (recipe version, model id, CLI version) if applicable",
    )
    captured_at: datetime = Field(..., description="When the underlying state was actually true (RFC3339 UTC)")
    source_type: SourceType = Field(..., description="Kind of source the body represents")
    source_uri: str = Field(
        ...,
        min_length=1,
        description="Path / URL / ARN / git ref. Meaning depends on source_type",
    )
    source_version: str | None = Field(
        default=None,
        description="Commit SHA, S3 versionId, document revision, etc.",
    )
    content_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="sha256 hex digest of the canonical body for tamper detection",
    )
    redaction_summary: RedactionSummary | None = Field(
        default=None,
        description="Redaction counts when the body was transformed; None when nothing was redacted",
    )
    recipe_selection: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Structured recipe-selection record populated by WS5 workflow integrations. "
            "Shape will be tightened to a typed RecipeSelection model when WS5 ships."
        ),
    )

    @field_validator("content_hash")
    @classmethod
    def _content_hash_must_be_lowercase_hex(cls, value: str) -> str:
        """sha256 hex digest is 64 lowercase hex chars by convention."""
        if not all(c in "0123456789abcdef" for c in value):
            raise ValueError("content_hash must be a lowercase hex sha256 digest (64 chars, 0-9a-f)")
        return value


class EvidenceCreate(BaseModel):
    """Data for creating evidence on the platform.

    Issue #79: evidence_type is required and must be one of the 13 canonical
    values defined in pretorin.evidence.types.VALID_EVIDENCE_TYPES. Callers
    who receive a possibly-AI-generated value should run
    normalize_evidence_type() first; this model is the last-line defense.
    """

    name: str = Field(..., description="Evidence name")
    description: str = Field(..., description="Evidence description")
    evidence_type: str = Field(..., description="Type of evidence")
    source: str = Field(default="cli", description="Source of evidence")
    control_id: str | None = Field(default=None, description="Associated control ID")
    framework_id: str | None = Field(default=None, description="Associated framework ID")
    code_snippet: str | None = Field(default=None, description="Relevant code excerpt")
    code_file_path: str | None = Field(default=None, description="Path to source file")
    code_line_numbers: str | None = Field(default=None, description="Line range (e.g., '10-25')")
    code_repository: str | None = Field(default=None, description="Git repository URL")
    code_commit_hash: str | None = Field(default=None, description="Git commit hash")
    audit_metadata: EvidenceAuditMetadata | None = Field(
        default=None,
        description=(
            "Audit-trail metadata (recipe-implementation WS1a). Optional during "
            "the migration window; will be required after WS1c lands platform-side."
        ),
    )

    @field_validator("evidence_type")
    @classmethod
    def _evidence_type_must_be_canonical(cls, value: str) -> str:
        from pretorin.evidence.types import VALID_EVIDENCE_TYPES

        if value not in VALID_EVIDENCE_TYPES:
            raise ValueError(
                f"evidence_type {value!r} is not one of the canonical values: {sorted(VALID_EVIDENCE_TYPES)}"
            )
        return value


class EvidenceBatchItemCreate(BaseModel):
    """One scoped evidence item in a batch create request."""

    name: str
    description: str
    control_id: str
    evidence_type: str
    relevance_notes: str | None = None
    code_snippet: str | None = None
    code_file_path: str | None = None
    code_line_numbers: str | None = None
    code_repository: str | None = None
    code_commit_hash: str | None = None
    audit_metadata: EvidenceAuditMetadata | None = Field(
        default=None,
        description=(
            "Audit-trail metadata (recipe-implementation WS1a). Optional during "
            "the migration window; will be required after WS1c lands platform-side."
        ),
    )

    @field_validator("evidence_type")
    @classmethod
    def _evidence_type_must_be_canonical(cls, value: str) -> str:
        from pretorin.evidence.types import VALID_EVIDENCE_TYPES

        if value not in VALID_EVIDENCE_TYPES:
            raise ValueError(
                f"evidence_type {value!r} is not one of the canonical values: {sorted(VALID_EVIDENCE_TYPES)}"
            )
        return value


class EvidenceBatchItemResult(BaseModel):
    """Per-item result from the batch evidence endpoint."""

    index: int
    status: str
    evidence_id: str | None = None
    mapping_id: str | None = None
    control_id: str | None = None
    framework_id: str | None = None
    error: str | None = None


class EvidenceBatchResponse(BaseModel):
    """Batch evidence response for a single system/framework scope."""

    framework_id: str
    total: int
    results: list[EvidenceBatchItemResult] = Field(default_factory=list)


# =============================================================================
# Narrative Models
# =============================================================================


class NarrativeResponse(BaseModel):
    """AI-generated narrative response."""

    control_id: str
    framework_id: str | None = None
    narrative: str | None = None
    ai_confidence_score: float | None = None
    status: str | None = None


# =============================================================================
# Control Implementation Models
# =============================================================================


class ControlImplementationResponse(BaseModel):
    """Control implementation details for a system."""

    control_id: str
    status: str | None = None
    implementation_narrative: str | None = None
    ai_generated_narrative: str | None = None
    ai_confidence_score: float | None = None
    evidence_count: int = 0
    notes: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("notes", mode="before")
    @classmethod
    def _coerce_null_notes(cls, value: Any) -> list[dict[str, Any]]:
        """Treat null notes from older platform deployments as an empty list."""
        if value is None:
            return []
        return cast(list[dict[str, Any]], value)

    @property
    def narrative(self) -> str | None:
        """Return the best available narrative (user-written takes precedence)."""
        return self.implementation_narrative or self.ai_generated_narrative


# =============================================================================
# Monitoring Models
# =============================================================================


class ControlContext(BaseModel):
    """Rich context combining OSCAL control data with implementation details."""

    control_id: str
    title: str | None = None
    statement: str | None = None
    guidance: str | None = None
    objectives: list[str] = Field(default_factory=list)
    ai_guidance: dict[str, Any] | None = None
    control_type: str | None = None
    status: str | None = None
    implementation_narrative: str | None = None
    user_context: str | None = None


class ReviewGap(BaseModel):
    """One persisted review gap."""

    area: str
    severity: str
    description: str


class ReviewChange(BaseModel):
    """One persisted recommended change."""

    section: str
    change: str
    suggested_bullet: str | None = None
    priority: str


class PersistedReview(BaseModel):
    """Normalized persisted AI review payload."""

    readiness: str | None = None
    completeness: dict[str, Any] = Field(default_factory=dict)
    accuracy: dict[str, Any] = Field(default_factory=dict)
    gaps: list[ReviewGap] = Field(default_factory=list)
    recommended_changes: list[ReviewChange] = Field(default_factory=list)


class QuestionGuidance(BaseModel):
    """Guidance metadata for a questionnaire item."""

    tips: list[str] = Field(default_factory=list)
    what_to_include: str | None = None
    example_response: str | None = None
    common_mistakes: list[str] = Field(default_factory=list)

    @field_validator("common_mistakes", mode="before")
    @classmethod
    def _coerce_common_mistakes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str):
            return [value] if value.strip() else []
        return []


class ScopeQuestionDefinition(BaseModel):
    """Canonical scope question definition from the platform."""

    id: str
    question: str
    section: str
    section_title: str
    order: int
    guidance: QuestionGuidance = Field(default_factory=QuestionGuidance)


class ScopeResponse(BaseModel):
    """System scope/policy information."""

    scope_status: str = "not_started"
    scope_narrative: dict[str, Any] | None = None
    scope_qa_responses: dict[str, Any] | None = None
    scope_questions: list[ScopeQuestionDefinition] = Field(default_factory=list)
    excluded_controls: list[str] = Field(default_factory=list)
    excluded_families: list[str] = Field(default_factory=list)
    inherited_controls: list[str] = Field(default_factory=list)
    scope_completed_at: str | None = None
    scope_completed_by: str | None = None
    scope_document_evidence_id: str | None = None
    scope_review: PersistedReview | None = None
    scope_reviewed_at: str | None = None


class MonitoringEventCreate(BaseModel):
    """Data for creating a monitoring event."""

    event_type: str = Field(default="security_scan", description="Event type")
    title: str = Field(..., description="Event title")
    description: str = Field(default="", description="Event description")
    severity: str = Field(default="high", description="Event severity")
    control_id: str | None = Field(default=None, description="Associated control ID")
    framework_id: str | None = Field(default=None, description="Associated framework ID")
    event_data: dict[str, Any] = Field(default_factory=dict, description="Additional event data")


class PolicyTemplateSection(BaseModel):
    """Canonical policy template section."""

    section_id: str
    title: str
    parent_section_id: str | None = None
    order: int
    template_guidance: str | None = None
    required_content: list[str] = Field(default_factory=list)


class PolicyQuestionDefinition(BaseModel):
    """Canonical policy question definition."""

    question_id: str
    question: str
    section_id: str
    additional_section_ids: list[str] = Field(default_factory=list)
    guidance: QuestionGuidance = Field(default_factory=QuestionGuidance)
    order: int


class PolicyTemplate(BaseModel):
    """Merged policy template with sections and questions."""

    template_id: str
    template_name: str
    document_type: str
    description: str | None = None
    version: str | None = None
    sections: list[PolicyTemplateSection] = Field(default_factory=list)
    questions: list[PolicyQuestionDefinition] = Field(default_factory=list)


class OrgPolicySummary(BaseModel):
    """Discovery metadata for one org policy."""

    id: str
    name: str
    policy_template_id: str | None = None
    status: str
    policy_qa_status: str | None = None
    policy_reviewed_at: str | None = None


class OrgPolicyListResponse(BaseModel):
    """List of org policies."""

    policies: list[OrgPolicySummary] = Field(default_factory=list)
    total: int = 0


class OrgPolicyQuestionnaireResponse(BaseModel):
    """Stateful questionnaire payload for one org policy."""

    policy_id: str
    name: str
    policy_template_id: str | None = None
    policy_qa_status: str | None = None
    policy_qa_responses: dict[str, Any] | None = None
    template: PolicyTemplate | None = None
    policy_review: PersistedReview | None = None
    policy_reviewed_at: str | None = None
