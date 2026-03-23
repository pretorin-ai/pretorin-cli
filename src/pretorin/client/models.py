"""Pydantic models for Pretorin API."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field, field_validator

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
    class_type: str = Field(alias="class")
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
# Error Models
# =============================================================================


class APIError(BaseModel):
    """API error response."""

    detail: str
    error: str | None = None
    message: str | None = None


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


class ArtifactSubmissionResult(BaseModel):
    """Result of artifact submission to the Pretorin API."""

    artifact_id: str = Field(..., description="Created artifact ID")
    url: str | None = Field(default=None, description="URL to view artifact")
    message: str = Field(default="Artifact submitted successfully")


# =============================================================================
# System Models
# =============================================================================


class SystemSummary(BaseModel):
    """Summary information about a system."""

    id: str
    name: str
    description: str | None = None
    security_impact_level: str | None = None


class SystemDetail(BaseModel):
    """Detailed system information."""

    id: str
    name: str
    description: str | None = None
    frameworks: list[dict[str, Any]] = Field(default_factory=list)
    security_impact_level: str | None = None


class ComplianceStatusResponse(BaseModel):
    """Compliance status for a system."""

    system_id: str
    system_name: str | None = None
    frameworks: list[dict[str, Any]] = Field(default_factory=list)


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


class EvidenceCreate(BaseModel):
    """Data for creating evidence on the platform."""

    name: str = Field(..., description="Evidence name")
    description: str = Field(..., description="Evidence description")
    evidence_type: str = Field(default="policy_document", description="Type of evidence")
    source: str = Field(default="cli", description="Source of evidence")
    control_id: str | None = Field(default=None, description="Associated control ID")
    framework_id: str | None = Field(default=None, description="Associated framework ID")


class EvidenceBatchItemCreate(BaseModel):
    """One scoped evidence item in a batch create request."""

    name: str
    description: str
    control_id: str
    evidence_type: str = Field(default="policy_document")
    relevance_notes: str | None = None


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


class ScopeQuestionResponse(BaseModel):
    """Saved scope Q&A item."""

    id: str
    question: str
    answer: str | None = None
    section: str


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


class MonitoringEventResponse(BaseModel):
    """Monitoring event response from the platform."""

    id: str
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    control_id: str | None = None
    framework_id: str | None = None
    status: str | None = None
    created_at: str | None = None


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


class PolicyQuestionResponse(BaseModel):
    """Saved policy Q&A item."""

    id: str
    question: str
    answer: str | None = None
    section_id: str


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
