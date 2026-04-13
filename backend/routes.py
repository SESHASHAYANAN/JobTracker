"""FastAPI routes — REST API for jobs, companies, founders, cold messages, resume matching."""
from __future__ import annotations
from fastapi import APIRouter, Query, UploadFile, File, Form
from typing import Optional
from models import ColdMessageRequest, ColdMessageResponse, HealthResponse
from store import store
from services.groq_service import generate_cold_dm, generate_cold_email
from services.resume_parser import extract_text_from_pdf, extract_skills, extract_experience_level, extract_role_preferences
from services.resume_matcher import match_jobs_to_resume

router = APIRouter(prefix="/api")


@router.get("/jobs")
async def get_jobs(
    role: Optional[str] = Query(None),
    visa: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    vc: Optional[str] = Query(None),
    batch: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    funding_min: Optional[int] = Query(None),
    funding_max: Optional[int] = Query(None),
    team_size_bucket: Optional[str] = Query(None),
    founder_name: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
):
    """Paginated jobs with server-side filtering. Excludes inactive companies."""
    jobs, total = store.get_jobs(
        role=role,
        visa=visa,
        country=country,
        stage=stage,
        vc=vc,
        batch=batch,
        level=level,
        funding_min=funding_min,
        funding_max=funding_max,
        team_size_bucket=team_size_bucket,
        founder_name=founder_name,
        search=search,
        page=page,
        limit=limit,
    )
    return {
        "jobs": [j.model_dump() for j in jobs],
        "total": total,
        "page": page,
        "limit": limit,
        "has_more": (page * limit) < total,
    }


@router.get("/companies/{slug}")
async def get_company(slug: str):
    """Full company record with all jobs and founders."""
    jobs = store.get_company(slug)
    if not jobs:
        return {"error": "Company not found", "jobs": [], "company": None}
    first = jobs[0]
    return {
        "company": {
            "name": first.company_name,
            "website": first.company_website,
            "slug": first.company_slug,
            "batch": first.batch,
            "stage": first.stage,
            "team_size": first.team_size,
            "founded_year": first.founded_year,
            "funding_total": first.funding_total,
            "vc_backers": first.vc_backers,
            "founders": [f.model_dump() for f in first.founders],
            "industry_tags": first.industry_tags,
        },
        "jobs": [j.model_dump() for j in jobs],
    }


@router.post("/cold-message", response_model=ColdMessageResponse)
async def cold_message(req: ColdMessageRequest):
    """Generate a cold DM using Groq for a specific job."""
    job = store.get_job_by_id(req.job_id)
    if not job:
        return ColdMessageResponse(
            job_id=req.job_id,
            message="Could not find job to generate message for.",
        )
    founder_name = job.founders[0].name if job.founders else "the hiring team"
    msg = await generate_cold_dm(
        company_name=job.company_name,
        role_title=job.role_title,
        founder_name=founder_name,
        candidate_profile=req.candidate_profile,
    )
    # Cache the message on the job
    job.cold_message = msg
    store.update_job(job)
    return ColdMessageResponse(
        job_id=req.job_id,
        message=msg,
        founder_name=founder_name,
    )


@router.get("/founders/search")
async def search_founders(q: str = Query("", min_length=1)):
    """Search founders by name or company."""
    results = store.search_founders(q)
    return {"founders": results, "total": len(results)}


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check with job count and last crawl time."""
    return HealthResponse(
        status="ok",
        job_count=store.count,
        last_crawl=store.last_crawl,
        agents_completed=store.agents_completed,
    )


# ── Resume Upload & Matching ─────────────────────────────
@router.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload a resume PDF, extract content, match to jobs."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Please upload a PDF file", "matches": []}

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        return {"error": "File too large (max 10MB)", "matches": []}

    resume_text = extract_text_from_pdf(contents)
    if not resume_text or len(resume_text.strip()) < 50:
        return {"error": "Could not extract text from PDF. Please ensure the PDF contains readable text.", "matches": []}

    # Extract profile info
    skills = extract_skills(resume_text)
    level = extract_experience_level(resume_text)
    role_prefs = extract_role_preferences(resume_text)

    # Match against all jobs
    all_jobs = list(store._jobs.values())
    matches = match_jobs_to_resume(resume_text, all_jobs, top_k=20)

    return {
        "matches": matches,
        "profile": {
            "skills": skills[:20],
            "experience_level": level,
            "role_preferences": role_prefs,
            "resume_length": len(resume_text),
        },
        "total_matched": len(matches),
    }


@router.post("/resume/cold-email")
async def resume_cold_email(
    job_id: str = Form(...),
    resume_text: str = Form(...),
):
    """Generate a personalized cold email based on resume + job."""
    job = store.get_job_by_id(job_id)
    if not job:
        return {"error": "Job not found", "email": ""}

    founder_name = job.founders[0].name if job.founders else "the hiring manager"
    founder_email = None
    founder_linkedin = None
    if job.founders:
        founder_email = job.founders[0].email
        founder_linkedin = job.founders[0].linkedin

    email = await generate_cold_email(
        company_name=job.company_name,
        role_title=job.role_title,
        founder_name=founder_name,
        resume_text=resume_text[:3000],  # Limit to avoid token limits
        job_description=job.jd_summary or job.job_description or "",
    )

    return {
        "email": email,
        "founder_name": founder_name,
        "founder_email": founder_email,
        "founder_linkedin": founder_linkedin,
        "company_name": job.company_name,
        "role_title": job.role_title,
    }

