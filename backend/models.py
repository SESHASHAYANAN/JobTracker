"""Pydantic data models for Job, Founder, Company."""
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

    def generate_id(self) -> str:
        raw = f"{self.company_slug}|{self.role_title}|{self.country or ''}|{self.city or ''}"
        self.id = hashlib.md5(raw.encode()).hexdigest()
        return self.id


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
