"""Pydantic models for Pretorin API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Status of a compliance check."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    """Severity level for compliance issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserInfo(BaseModel):
    """Information about the authenticated user."""

    id: str
    email: str
    name: str | None = None
    organization: str | None = None
    organization_id: str | None = None
    created_at: datetime | None = None


class ComplianceIssue(BaseModel):
    """A single compliance issue found during a check."""

    id: str
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    location: str | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComplianceCheck(BaseModel):
    """A compliance check request."""

    id: str
    status: ComplianceStatus
    file_name: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    issues: list[ComplianceIssue] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ComplianceReport(BaseModel):
    """A compliance report."""

    id: str
    name: str
    status: ComplianceStatus
    created_at: datetime
    completed_at: datetime | None = None
    checks: list[ComplianceCheck] = Field(default_factory=list)
    total_issues: int = 0
    issues_by_severity: dict[str, int] = Field(default_factory=dict)


class ReportListItem(BaseModel):
    """Summary item for listing reports."""

    id: str
    name: str
    status: ComplianceStatus
    created_at: datetime
    total_issues: int = 0


class APIError(BaseModel):
    """API error response."""

    error: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
