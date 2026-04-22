"""FastAPI routes bridging the frontend to the Python agent suite.

These routes wrap the CLI-oriented agents as HTTP endpoints so the
React frontend can invoke them.  All routes live under /api/agents/*
and do NOT touch any existing /api/* routes.
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Query, UploadFile, File, Form
from pydantic import BaseModel

# ── Ensure the project root is on sys.path so `agents` package resolves ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.config import DATA_DIR, validate_config
from agents.models import (
    ScanResult, ScoringResult, TailoredCV, BatchResult,
    PipelineEntry, PipelineAnalytics, JobStatus,
)

agent_router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Request / Response schemas ───────────────────────────────────────

class ScoreRequest(BaseModel):
    url: Optional[str] = None
    jd_text: Optional[str] = None
    cv_text: Optional[str] = None
    company: Optional[str] = ""
    role: Optional[str] = ""


class TailorRequest(BaseModel):
    url: Optional[str] = None
    jd_text: Optional[str] = None
    cv_text: Optional[str] = None
    company: Optional[str] = ""
    role: Optional[str] = ""


class BatchRequest(BaseModel):
    urls: list[str] = []
    cv_text: Optional[str] = None
    concurrency: int = 5


class StatusUpdateRequest(BaseModel):
    company: str
    role: str
    new_status: str


# ── Helpers ──────────────────────────────────────────────────────────

def _load_default_cv() -> str:
    """Load CV from agents/data/cv.md if it exists."""
    for candidate in [
        DATA_DIR / "cv.md",
        _PROJECT_ROOT / "cv.md",
    ]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return ""


# ── Health / Config ──────────────────────────────────────────────────

@agent_router.get("/health")
async def agent_health():
    """Health check for agent subsystem."""
    warnings = validate_config()
    return {
        "status": "ok" if not warnings else "degraded",
        "warnings": warnings,
        "cv_loaded": bool(_load_default_cv()),
        "data_dir": str(DATA_DIR),
    }


# ── Scan ─────────────────────────────────────────────────────────────

@agent_router.post("/scan")
async def run_scan(
    company: Optional[str] = Body(None),
    dry_run: bool = Body(False),
):
    """Trigger a portal scan via JobScanAgent."""
    try:
        from agents.job_scan.agent import JobScanAgent
        agent = JobScanAgent()
        result: ScanResult = await agent.scan_all(
            dry_run=dry_run,
            company_filter=company,
        )
        return {
            "status": "ok",
            "date": result.date,
            "companies_scanned": result.companies_scanned,
            "total_found": result.total_found,
            "filtered_by_title": result.filtered_by_title,
            "duplicates": result.duplicates,
            "new_offers": [j.model_dump() for j in result.new_offers],
            "errors": result.errors,
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Score ────────────────────────────────────────────────────────────

@agent_router.post("/score")
async def run_score(req: ScoreRequest):
    """Evaluate a job description using ScoringAgent."""
    try:
        cv_text = req.cv_text or _load_default_cv()
        if not cv_text:
            return {"status": "error", "error": "No CV provided and no default cv.md found"}

        from agents.scoring.agent import ScoringAgent
        agent = ScoringAgent()

        if req.url:
            result: ScoringResult = await agent.evaluate_url(req.url, cv_text)
        elif req.jd_text:
            result = await agent.evaluate(
                req.jd_text, cv_text,
                company=req.company or "",
                role=req.role or "",
            )
        else:
            return {"status": "error", "error": "Provide a URL or jd_text"}

        return {
            "status": "ok",
            "company": result.company,
            "role": result.role,
            "archetype": result.archetype.value,
            "archetype_confidence": result.archetype_confidence,
            "dimensions": [d.model_dump() for d in result.dimensions],
            "overall_score": result.overall_score,
            "grade": result.grade.value,
            "recommendation": result.recommendation,
            "cv_match_summary": result.cv_match_summary,
            "gaps": result.gaps,
            "gap_mitigations": result.gap_mitigations,
            "keywords": result.keywords,
            "report_path": result.report_path,
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Tailor ───────────────────────────────────────────────────────────

@agent_router.post("/tailor")
async def run_tailor(req: TailorRequest):
    """Generate a tailored CV using CVTailorAgent."""
    try:
        cv_text = req.cv_text or _load_default_cv()
        if not cv_text:
            return {"status": "error", "error": "No CV provided and no default cv.md found"}

        from agents.cv_tailor.agent import CVTailorAgent
        agent = CVTailorAgent()

        if req.url:
            result: TailoredCV = await agent.tailor_from_url(cv_text, req.url)
        elif req.jd_text:
            result = await agent.tailor(
                cv_text, req.jd_text,
                company=req.company or "",
                role=req.role or "",
            )
        else:
            return {"status": "error", "error": "Provide a URL or jd_text"}

        return {
            "status": "ok",
            "sections": [s.model_dump() for s in result.sections],
            "keywords_injected": result.keywords_injected,
            "keyword_coverage": result.keyword_coverage,
            "ats_score": result.ats_score,
            "html_path": result.html_path,
            "pdf_path": result.pdf_path,
            "page_count": result.page_count,
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Batch ────────────────────────────────────────────────────────────

@agent_router.post("/batch")
async def run_batch(req: BatchRequest):
    """Process multiple URLs via BatchAgent."""
    try:
        cv_text = req.cv_text or _load_default_cv()
        if not cv_text:
            return {"status": "error", "error": "No CV provided and no default cv.md found"}

        if not req.urls:
            return {"status": "error", "error": "No URLs provided"}

        from agents.batch.agent import BatchAgent
        agent = BatchAgent(concurrency=req.concurrency)
        result: BatchResult = await agent.process_urls(req.urls, cv_text)

        return {
            "status": "ok",
            "total": result.total,
            "completed": result.completed,
            "failed": result.failed,
            "skipped": result.skipped,
            "elapsed_seconds": result.elapsed_seconds,
            "results": [j.model_dump() for j in result.results],
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


@agent_router.get("/batch/status")
async def batch_status():
    """Get current batch processing status."""
    try:
        from agents.batch.agent import BatchAgent
        agent = BatchAgent()
        status = agent.get_status()
        return {"status": "ok", **status}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Tracker ──────────────────────────────────────────────────────────

@agent_router.get("/tracker")
async def get_tracker(
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """Get all pipeline entries, optionally filtered by status."""
    try:
        from agents.tracker.agent import TrackerAgent
        agent = TrackerAgent()
        entries = agent.get_entries(status=status_filter)
        summary = await agent.get_summary()
        return {
            "status": "ok",
            "entries": [e.model_dump() for e in entries],
            "summary": summary.model_dump(),
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


@agent_router.get("/tracker/analytics")
async def get_tracker_analytics():
    """Get pipeline analytics."""
    try:
        from agents.tracker.agent import TrackerAgent
        agent = TrackerAgent()
        analytics: PipelineAnalytics = await agent.get_analytics()
        return {
            "status": "ok",
            "analytics": analytics.model_dump(),
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


@agent_router.put("/tracker/status")
async def update_tracker_status(req: StatusUpdateRequest):
    """Update the status of a tracked application."""
    try:
        from agents.tracker.agent import TrackerAgent
        agent = TrackerAgent()
        success = await agent.update_status(req.company, req.role, req.new_status)
        return {
            "status": "ok" if success else "not_found",
            "updated": success,
        }
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "error": str(e)}
