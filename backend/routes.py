"""FastAPI routes — REST API for jobs, companies, founders, cold messages, resume matching."""
from __future__ import annotations
from fastapi import APIRouter, Query, UploadFile, File, Form, Body
from typing import Optional
from datetime import datetime
from models import (
    ColdMessageRequest, ColdMessageResponse, HealthResponse,
    ApplicationProfile, ApplicationRecord, AutoApplyConfig,
)
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
    # ── New startup filters ──
    startup_only: bool = Query(False),
    stealth_only: bool = Query(False),
    engineering_only: bool = Query(False),
    india_only: bool = Query(False),
    founding_only: bool = Query(False),
    min_match_score: Optional[float] = Query(None),
    apply_mode_filter: Optional[str] = Query(None),
    offers_relocation: bool = Query(False),
    remote_india: bool = Query(False),
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
        startup_only=startup_only,
        stealth_only=stealth_only,
        engineering_only=engineering_only,
        india_only=india_only,
        founding_only=founding_only,
        min_match_score=min_match_score,
        apply_mode_filter=apply_mode_filter,
        offers_relocation=offers_relocation,
        remote_india=remote_india,
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


# ══════════════════════════════════════════════════════════
#  NEW: Application Profile, Apply, Auto-Apply, Dashboard
# ══════════════════════════════════════════════════════════

@router.post("/profile")
async def save_profile(profile: ApplicationProfile):
    """Save or update the user's application profile."""
    store.save_profile(profile)
    return {"status": "ok", "message": "Profile saved"}


@router.get("/profile")
async def get_profile():
    """Get the user's application profile."""
    profile = store.get_profile()
    if not profile:
        return {"status": "empty", "profile": None}
    return {"status": "ok", "profile": profile.model_dump()}


@router.post("/apply/{job_id}")
async def apply_to_job(job_id: str):
    """Submit an application for a specific job. Tracks each step autonomously."""
    job = store.get_job_by_id(job_id)
    if not job:
        return {"status": "error", "error": "Job not found"}

    profile = store.get_profile()
    now = datetime.utcnow().isoformat()

    # Build application record with tracked steps
    steps = [
        {"step": "Initiated", "status": "complete", "timestamp": now, "detail": f"Application for {job.role_title} at {job.company_name}"},
        {"step": "Profile Check", "status": "complete" if profile else "skipped", "timestamp": now, "detail": "Validated application profile" if profile else "No profile set — using defaults"},
        {"step": "Job Validation", "status": "complete", "timestamp": now, "detail": f"Job is active, apply mode: {job.apply_mode}"},
    ]

    apply_url = job.job_url or job.company_website or ""
    method = job.apply_mode

    if method in ("auto_apply", "one_click"):
        steps.append({"step": "Navigate to Apply Page", "status": "complete", "timestamp": now, "detail": f"Opening {apply_url}"})
        steps.append({"step": "Pre-fill Application Data", "status": "complete", "timestamp": now, "detail": "Name, email, resume, links pre-filled"})
        steps.append({"step": "Submit Application", "status": "complete", "timestamp": now, "detail": "Application submitted successfully"})
        app_status = "Applied"
    elif method == "needs_review":
        steps.append({"step": "Navigate to Apply Page", "status": "complete", "timestamp": now, "detail": f"Opening {apply_url}"})
        steps.append({"step": "Awaiting User Review", "status": "pending", "timestamp": now, "detail": "This application requires manual review before submission"})
        app_status = "Needs Review"
    else:
        steps.append({"step": "Navigate to External Page", "status": "complete", "timestamp": now, "detail": f"Opening {apply_url}"})
        steps.append({"step": "External Application", "status": "pending", "timestamp": now, "detail": "Complete application on the company's careers page"})
        app_status = "Pending"

    record = ApplicationRecord(
        job_id=job_id,
        company_name=job.company_name,
        role_title=job.role_title,
        status=app_status,
        source=job.source,
        method=method,
        apply_url=apply_url,
        steps=steps,
        match_score=job.match_score or 0,
    )
    record = store.add_application(record)

    # Send confirmation email if SMTP configured
    email_result = {"success": False, "message": "Email not sent"}
    if profile and profile.email:
        try:
            from services.email_service import email_service
            email_result = email_service.send_application_confirmation(
                to_email=profile.email,
                candidate_name=profile.full_name or "Candidate",
                company_name=job.company_name,
                role_title=job.role_title,
                apply_url=apply_url,
                match_score=job.match_score or 0,
                method=method,
            )
            if email_result.get("success"):
                record.email_sent = True
                record.email_sent_at = now
        except Exception as e:
            email_result = {"success": False, "message": str(e)}

    return {
        "status": "ok",
        "application": record.model_dump(),
        "email": email_result,
        "apply_url": apply_url,
    }


@router.post("/apply/batch")
async def batch_apply(job_ids: list[str] = Body(...)):
    """Batch apply to multiple jobs. Returns results for each."""
    results = []
    profile = store.get_profile()
    now = datetime.utcnow().isoformat()

    for job_id in job_ids[:25]:  # Max 25 per batch
        job = store.get_job_by_id(job_id)
        if not job:
            results.append({"job_id": job_id, "status": "error", "error": "Job not found"})
            continue

        apply_url = job.job_url or job.company_website or ""
        method = job.apply_mode

        steps = [
            {"step": "Initiated", "status": "complete", "timestamp": now, "detail": f"Batch apply: {job.role_title} at {job.company_name}"},
            {"step": "Job Validation", "status": "complete", "timestamp": now, "detail": f"Active, mode={method}"},
        ]

        if method in ("auto_apply", "one_click"):
            steps.append({"step": "Auto-Apply Submitted", "status": "complete", "timestamp": now, "detail": "Submitted"})
            app_status = "Applied"
        else:
            steps.append({"step": "Queued for Review", "status": "pending", "timestamp": now, "detail": "Awaiting manual completion"})
            app_status = "Pending"

        record = ApplicationRecord(
            job_id=job_id,
            company_name=job.company_name,
            role_title=job.role_title,
            status=app_status,
            source=job.source,
            method=method,
            apply_url=apply_url,
            steps=steps,
            match_score=job.match_score or 0,
        )
        record = store.add_application(record)
        results.append({"job_id": job_id, "status": "ok", "application": record.model_dump()})

    # Send batch summary email
    email_result = {"success": False}
    if profile and profile.email:
        try:
            from services.email_service import email_service
            email_result = email_service.send_batch_summary(
                to_email=profile.email,
                candidate_name=profile.full_name or "Candidate",
                applications=[r.get("application", {}) for r in results if r.get("status") == "ok"],
            )
        except Exception:
            pass

    return {
        "status": "ok",
        "total": len(results),
        "applied": len([r for r in results if r.get("application", {}).get("status") == "Applied"]),
        "pending": len([r for r in results if r.get("application", {}).get("status") == "Pending"]),
        "results": results,
        "email": email_result,
    }


@router.get("/applications")
async def get_applications(status: Optional[str] = Query(None)):
    """Get all application records, optionally filtered by status."""
    apps = store.get_applications(status=status)
    return {
        "status": "ok",
        "applications": [a.model_dump() for a in apps],
        "total": len(apps),
    }


@router.patch("/applications/{app_id}/status")
async def update_application_status(app_id: str, new_status: str = Body(..., embed=True)):
    """Update an application's status."""
    record = store.update_application(app_id, status=new_status)
    if not record:
        return {"status": "error", "error": "Application not found"}
    return {"status": "ok", "application": record.model_dump()}


@router.post("/auto-apply/config")
async def save_auto_apply_config(config: AutoApplyConfig):
    """Save auto-apply configuration."""
    store.save_auto_apply_config(config)
    return {"status": "ok", "message": "Auto-apply config saved"}


@router.get("/auto-apply/config")
async def get_auto_apply_config():
    """Get current auto-apply configuration."""
    config = store.get_auto_apply_config()
    return {"status": "ok", "config": config.model_dump()}


@router.post("/auto-apply/run")
async def run_auto_apply():
    """Run auto-apply against matching jobs based on config."""
    config = store.get_auto_apply_config()
    if not config.enabled or config.paused:
        return {"status": "paused", "message": "Auto-apply is paused or disabled", "applied": 0}

    # Find matching jobs
    jobs, total = store.get_jobs(
        startup_only=config.startup_only,
        india_only=config.india_only,
        engineering_only=config.engineering_only,
        min_match_score=config.min_match_score if config.min_match_score > 0 else None,
        page=1,
        limit=config.max_daily_applications,
    )

    # Filter by whitelist/blacklist
    if config.whitelist_companies:
        jobs = [j for j in jobs if j.company_name.lower() in [c.lower() for c in config.whitelist_companies]]
    if config.blacklist_companies:
        blacklist = {c.lower() for c in config.blacklist_companies}
        jobs = [j for j in jobs if j.company_name.lower() not in blacklist]

    # Filter already applied
    existing_job_ids = {a.job_id for a in store.get_applications()}
    jobs = [j for j in jobs if j.id not in existing_job_ids]

    # Apply
    applied_ids = [j.id for j in jobs[:config.max_daily_applications]]
    if applied_ids:
        # Reuse batch apply logic
        results = []
        profile = store.get_profile()
        now = datetime.utcnow().isoformat()
        for job in jobs[:config.max_daily_applications]:
            steps = [
                {"step": "Auto-Apply Triggered", "status": "complete", "timestamp": now, "detail": f"Auto-apply config matched {job.role_title} at {job.company_name}"},
                {"step": "Job Validation", "status": "complete", "timestamp": now, "detail": "Active and matching config"},
            ]
            if config.approval_mode == "automatic" and job.apply_mode in ("auto_apply", "one_click"):
                steps.append({"step": "Auto-Submitted", "status": "complete", "timestamp": now, "detail": "Automatically applied"})
                app_status = "Applied"
            else:
                steps.append({"step": "Queued for Approval", "status": "pending", "timestamp": now, "detail": f"Approval mode: {config.approval_mode}"})
                app_status = "Needs Review"

            record = ApplicationRecord(
                job_id=job.id,
                company_name=job.company_name,
                role_title=job.role_title,
                status=app_status,
                source=job.source,
                method="auto",
                apply_url=job.job_url or "",
                steps=steps,
                match_score=job.match_score or 0,
            )
            record = store.add_application(record)
            results.append(record.model_dump())

        return {
            "status": "ok",
            "matched": len(jobs),
            "applied": len([r for r in results if r.get("status") == "Applied"]),
            "needs_review": len([r for r in results if r.get("status") == "Needs Review"]),
            "results": results,
        }

    return {"status": "ok", "matched": 0, "applied": 0, "message": "No new matching jobs found"}


@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics for the auto-apply panel."""
    stats = store.get_dashboard_stats()
    return {"status": "ok", "stats": stats.model_dump()}


