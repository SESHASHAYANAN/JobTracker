"""Pydantic data models for Job, Founder, Company, Applications."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import hashlib


class Founder(BaseModel):
    name: str = ""
    title: str = ""  # CEO, CTO, Chief of Staff, etc.
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    email: Optional[str] = None
    source: str = ""


class Job(BaseModel):
    id: str = ""
    # Company
    company_name: str = ""
    company_website: Optional[str] = None
    company_slug: str = ""
    batch: Optional[str] = None  # YC batch e.g. W25, S24
    stage: Optional[str] = None  # Seed, Series A, etc.
    vc_backers: list[str] = Field(default_factory=list)
    team_size: Optional[int] = None
    founded_year: Optional[int] = None
    funding_total: Optional[str] = None
    status: str = "active"  # active / inactive
    is_hiring: bool = True
    # Role
    role_title: str = ""
    role_category: Optional[str] = None
    experience_level: Optional[str] = None  # New Grad, Mid, Senior
    visa_sponsorship: Optional[str] = None  # Yes / No / Unknown
    salary_range: Optional[str] = None
    work_type: Optional[str] = None  # onsite / remote / hybrid
    country: Optional[str] = None
    city: Optional[str] = None
    # Content
    job_url: Optional[str] = None
    job_description: Optional[str] = None
    jd_summary: Optional[str] = None
    source: str = ""
    scraped_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    # People
    founders: list[Founder] = Field(default_factory=list)
    # AI
    cold_message: Optional[str] = None
    relevance_score: float = 0.0
    industry_tags: list[str] = Field(default_factory=list)

    # ── Startup classification ────────────────────────────
    is_startup: bool = False
    is_stealth: bool = False
    startup_stage: Optional[str] = None  # Pre-Seed, Seed, Series A, etc.
    startup_tags: list[str] = Field(default_factory=list)
    startup_confidence: float = 0.0  # 0.0 – 1.0

    # ── Resume match ──────────────────────────────────────
    match_score: Optional[float] = None  # 0–100
    match_reasons: list[str] = Field(default_factory=list)

    # ── Application mode ──────────────────────────────────
    apply_mode: str = "external"  # auto_apply | one_click | needs_review | external

    # ── Freshness ─────────────────────────────────────────
    posted_date: Optional[str] = None
    last_seen: Optional[str] = None
    source_url: Optional[str] = None

    # ── Relocation ────────────────────────────────────────
    offers_relocation: bool = False
    relocation_countries: list[str] = Field(default_factory=list)

    # ── URL verification ──────────────────────────────────
    verified_url: Optional[str] = None
    url_verified: bool = False
    url_verification_error: Optional[str] = None

    def generate_id(self) -> str:
        raw = f"{self.company_slug}|{self.role_title}|{self.country or ''}|{self.city or ''}"
        self.id = hashlib.md5(raw.encode()).hexdigest()
        return self.id


# ── Application Profile ──────────────────────────────────

class ApplicationProfile(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    work_authorization: str = ""
    notice_period: str = ""
    years_of_experience: int = 0
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    resume_text: str = ""
    resume_file_path: Optional[str] = None  # Path to uploaded PDF on disk
    cover_letter_template: str = ""
    preferred_titles: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    preferred_stages: list[str] = Field(default_factory=list)
    preferred_tech_stack: list[str] = Field(default_factory=list)
    remote_preference: str = "any"  # any | remote | onsite | hybrid
    salary_expectation: str = ""
    blacklist_companies: list[str] = Field(default_factory=list)
    blacklist_domains: list[str] = Field(default_factory=list)
    include_stealth: bool = True
    auto_apply_mode: str = "manual"  # manual | approval | automatic


# ── Application Record ───────────────────────────────────

class ApplicationRecord(BaseModel):
    id: str = ""
    job_id: str = ""
    company_name: str = ""
    role_title: str = ""
    status: str = "Pending"  # Applied | Pending | Needs Review | Failed | Skipped
    applied_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""
    method: str = "external"  # auto | one_click | external
    apply_url: str = ""
    error_message: str = ""
    email_sent: bool = False
    email_sent_at: Optional[str] = None
    steps: list[dict] = Field(default_factory=list)  # [{step, status, timestamp}]
    match_score: float = 0.0

    def generate_id(self) -> str:
        raw = f"{self.job_id}|{self.applied_at}"
        self.id = hashlib.md5(raw.encode()).hexdigest()
        return self.id


# ── Auto-Apply Config ────────────────────────────────────

class AutoApplyConfig(BaseModel):
    enabled: bool = False
    startup_only: bool = True
    india_only: bool = False
    remote_india: bool = True
    engineering_only: bool = True
    min_match_score: float = 40.0
    salary_min: Optional[str] = None
    max_days_old: int = 30
    whitelist_companies: list[str] = Field(default_factory=list)
    blacklist_companies: list[str] = Field(default_factory=list)
    approval_mode: str = "approval"  # one_click | batch | automatic
    max_daily_applications: int = 25
    paused: bool = False


# ── Dashboard Stats ──────────────────────────────────────

class DashboardStats(BaseModel):
    total_jobs: int = 0
    total_startup_jobs: int = 0
    startup_percentage: float = 0.0
    india_jobs: int = 0
    engineering_jobs: int = 0
    auto_apply_eligible: int = 0
    applications_sent: int = 0
    pending_approvals: int = 0
    failed_applications: int = 0
    emails_sent: int = 0
    top_tech_stacks: list[dict] = Field(default_factory=list)
    top_startup_domains: list[dict] = Field(default_factory=list)
    stealth_jobs: int = 0
    relocation_jobs: int = 0


class ColdMessageRequest(BaseModel):
    job_id: str
    candidate_profile: Optional[str] = None


class ColdMessageResponse(BaseModel):
    job_id: str
    message: str
    founder_name: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    job_count: int = 0
    last_crawl: Optional[str] = None
    agents_completed: list[str] = Field(default_factory=list)
