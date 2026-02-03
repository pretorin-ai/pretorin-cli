"""Pydantic models for Pretorin API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


# =============================================================================
# Control Family Models
# =============================================================================


class ControlFamilySummary(BaseModel):
    """Summary of a control family."""

    id: str
    title: str
    class_type: str = Field(alias="class")
    controls_count: int = 0


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

    control_id: str = Field(..., description="Control ID (e.g., ac-2, au-2)")
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
    control_id: str = Field(..., description="Control ID (e.g., ac-2)")
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
