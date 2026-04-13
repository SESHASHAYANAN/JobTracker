"""Pydantic data models for the agent suite.

Self-contained — does NOT import from backend/models.py.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────

class PortalType(str, Enum):
    GREENHOUSE = "greenhouse"
    ASHBY = "ashby"
    LEVER = "lever"
    CUSTOM = "custom"


class Archetype(str, Enum):
    LLMOPS = "llmops"
    AGENTIC = "agentic"
    TECHNICAL_PM = "technical_pm"
    SOLUTIONS_ARCH = "solutions_arch"
    FORWARD_DEPLOYED = "forward_deployed"
    TRANSFORMATION = "transformation"
    GENERAL = "general"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class JobStatus(str, Enum):
    EVALUATED = "Evaluated"
    APPLIED = "Applied"
    RESPONDED = "Responded"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    DISCARDED = "Discarded"
    SKIP = "SKIP"


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Scanner Models ───────────────────────────────────────────────────

class PortalConfig(BaseModel):
    """Configuration for a single career portal."""
    name: str
    careers_url: Optional[str] = None
    api_url: Optional[str] = None
    portal_type: Optional[PortalType] = None
    enabled: bool = True
    category: str = "general"


class TitleFilterConfig(BaseModel):
    """Configuration for title-based job filtering."""
    positive: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)
    seniority_boost: list[str] = Field(default_factory=list)


class ScannedJob(BaseModel):
    """A job listing discovered by the scanner."""
    title: str
    url: str
    company: str
    location: str = ""
    source: str = ""
    discovered_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d")
    )


class ScanResult(BaseModel):
    """Aggregate result of a portal scan."""
    date: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d")
    )
    companies_scanned: int = 0
    total_found: int = 0
    filtered_by_title: int = 0
    duplicates: int = 0
    new_offers: list[ScannedJob] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


# ── Scoring Models ───────────────────────────────────────────────────

class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""
    name: str
    score: float = Field(ge=1.0, le=5.0)
    weight: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)


class ScoringResult(BaseModel):
    """Complete evaluation result for a job."""
    company: str
    role: str
    url: str = ""
    archetype: Archetype = Archetype.GENERAL
    archetype_confidence: float = 0.0
    dimensions: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = 0.0
    grade: Grade = Grade.F
    recommendation: str = ""
    cv_match_summary: str = ""
    gaps: list[str] = Field(default_factory=list)
    gap_mitigations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    report_path: Optional[str] = None
    evaluated_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d")
    )

    def compute_grade(self) -> Grade:
        """Map overall score to letter grade."""
        s = self.overall_score
        if s >= 4.5:
            return Grade.A
        elif s >= 4.0:
            return Grade.B
        elif s >= 3.5:
            return Grade.C
        elif s >= 3.0:
            return Grade.D
        elif s >= 2.5:
            return Grade.E
        else:
            return Grade.F

    def compute_overall(self) -> float:
        """Compute weighted average across all dimensions."""
        if not self.dimensions:
            return 0.0
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        weighted = sum(d.score * d.weight for d in self.dimensions)
        return round(weighted / total_weight, 2)


# ── CV Tailor Models ─────────────────────────────────────────────────

class TailoredSection(BaseModel):
    """A single rewritten CV section."""
    name: str
    original: str
    tailored: str
    keywords_used: list[str] = Field(default_factory=list)


class TailoredCV(BaseModel):
    """Result of CV tailoring."""
    sections: list[TailoredSection] = Field(default_factory=list)
    keywords_injected: list[str] = Field(default_factory=list)
    keyword_coverage: float = 0.0
    ats_score: float = 0.0
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    page_count: int = 1


# ── Batch Models ─────────────────────────────────────────────────────

class BatchJob(BaseModel):
    """A single item in a batch processing queue."""
    id: int
    url: str
    status: BatchStatus = BatchStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    report_num: Optional[int] = None
    score: Optional[float] = None
    error: Optional[str] = None
    retries: int = 0


class BatchResult(BaseModel):
    """Aggregate result of batch processing."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[BatchJob] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


# ── Tracker Models ───────────────────────────────────────────────────

class PipelineEntry(BaseModel):
    """A single row in the application tracker."""
    number: int
    date: str
    company: str
    role: str
    score: Optional[float] = None
    status: JobStatus = JobStatus.EVALUATED
    pdf_generated: bool = False
    report_link: Optional[str] = None
    notes: str = ""


class TrackerSummary(BaseModel):
    """Summary statistics for the pipeline."""
    total_entries: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    avg_score: float = 0.0
    top_companies: list[str] = Field(default_factory=list)
    last_updated: Optional[str] = None


class PipelineAnalytics(BaseModel):
    """Detailed analytics for the pipeline."""
    summary: TrackerSummary
    conversion_rates: dict[str, float] = Field(default_factory=dict)
    score_distribution: dict[str, int] = Field(default_factory=dict)
    archetype_breakdown: dict[str, int] = Field(default_factory=dict)
    weekly_activity: list[dict] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
