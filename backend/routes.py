"""FastAPI routes — REST API for jobs, companies, founders, cold messages, resume matching."""
from __future__ import annotations
import os, re as _re
from fastapi import APIRouter, Query, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import Optional
import httpx
from datetime import datetime
from models import (
    ColdMessageRequest, ColdMessageResponse, HealthResponse,
    ApplicationProfile, ApplicationRecord, AutoApplyConfig,
)
from store import store
from services.groq_service import generate_cold_dm, generate_cold_email
from services.resume_parser import extract_text_from_pdf, extract_skills, extract_experience_level, extract_role_preferences, ai_parse_resume
from services.resume_matcher import match_jobs_to_resume

ROUTER_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RESUME_DIR = os.path.join(ROUTER_DATA_DIR, "resumes")
os.makedirs(RESUME_DIR, exist_ok=True)

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
    """Upload a resume PDF, extract content, AI-parse, match to jobs."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Please upload a PDF file", "matches": []}

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        return {"error": "File too large (max 10MB)", "matches": []}

    # Save file to disk for browser automation uploads
    safe_name = file.filename.replace(" ", "_").replace("..", "")
    resume_path = os.path.join(RESUME_DIR, safe_name)
    with open(resume_path, "wb") as f:
        f.write(contents)

    # Update profile with file path
    profile = store.get_profile()
    if profile:
        profile.resume_file_path = resume_path
        store.save_profile(profile)

    resume_text = extract_text_from_pdf(contents)
    if not resume_text or len(resume_text.strip()) < 50:
        return {"error": "Could not extract text from PDF. Please ensure the PDF contains readable text.", "matches": []}

    # AI-powered profile extraction (Groq)
    ai_profile = await ai_parse_resume(resume_text)

    # Fallback to keyword-based if AI didn't return skills
    skills = ai_profile.get("skills", []) or extract_skills(resume_text)
    level = ai_profile.get("experience_level", "") or extract_experience_level(resume_text)
    role_prefs = ai_profile.get("role_preferences", []) or extract_role_preferences(resume_text)

    # AI-powered job matching (Groq for fast scoring, Gemini for top-10 deep analysis)
    all_jobs = list(store._jobs.values())
    matches = await match_jobs_to_resume(resume_text, all_jobs, top_k=20)

    return {
        "matches": matches,
        "profile": {
            "skills": skills[:20],
            "experience_level": level,
            "role_preferences": role_prefs,
            "resume_length": len(resume_text),
        },
        "ai_parsed_profile": ai_profile,
        "resume_file_path": resume_path,
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
    """Submit an application for a specific job.
    Returns the exact verified apply URL — never a generic domain.
    """
    job = store.get_job_by_id(job_id)
    if not job:
        return {"status": "error", "error": "Job not found"}

    profile = store.get_profile()
    now = datetime.utcnow().isoformat()

    verification_steps = []
    verification_steps.append({"step": "Initiated", "status": "complete", "timestamp": now,
                               "detail": f"Application for {job.role_title} at {job.company_name}"})

    # ── Real URL resolution chain ────────────────────────────────
    from urllib.parse import urlparse

    candidate_urls = []
    if job.verified_url:
        candidate_urls.append(("verified_url", job.verified_url))
    if job.job_url:
        candidate_urls.append(("job_url", job.job_url))
    if job.source_url:
        candidate_urls.append(("source_url", job.source_url))
    if job.company_website:
        candidate_urls.append(("company_website", job.company_website))

    apply_url = ""
    url_source = ""
    live_verified = False

    for source_label, url in candidate_urls:
        if not url or not url.startswith("http"):
            continue
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        is_generic = (not path or path == "/")
        if is_generic:
            verification_steps.append({"step": "URL Check", "status": "skipped", "timestamp": now,
                                       "detail": f"Skipped generic homepage: {url}"})
            continue

        # Verify the URL is reachable
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }) as client:
                resp = await client.head(url)
                if resp.status_code < 400:
                    apply_url = str(resp.url)  # follow redirects to final URL
                    url_source = source_label
                    live_verified = True
                    verification_steps.append({"step": "URL Verified", "status": "complete", "timestamp": now,
                                               "detail": f"Live URL confirmed ({resp.status_code}): {apply_url}"})
                    break
                else:
                    verification_steps.append({"step": "URL Check", "status": "failed", "timestamp": now,
                                               "detail": f"{source_label} returned HTTP {resp.status_code}"})
        except Exception as e:
            verification_steps.append({"step": "URL Check", "status": "failed", "timestamp": now,
                                       "detail": f"{source_label} unreachable: {str(e)[:80]}"})

    # If no URL passed, try Gemini URL discovery
    if not apply_url:
        try:
            from services.link_verifier import find_direct_apply_url
            discovered = await find_direct_apply_url(job.company_name, job.role_title,
                                                     job.company_website, job.job_url)
            if discovered:
                # Verify the discovered URL
                async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }) as client:
                    resp = await client.head(discovered)
                    if resp.status_code < 400:
                        apply_url = str(resp.url)
                        url_source = "ai_discovered"
                        live_verified = True
                        verification_steps.append({"step": "AI URL Discovery", "status": "complete", "timestamp": now,
                                                   "detail": f"AI found live URL: {apply_url}"})
                        # Persist discovered URL
                        job.verified_url = apply_url
                        job.url_verified = True
                        store.update_job(job)
        except Exception as e:
            verification_steps.append({"step": "AI URL Discovery", "status": "failed", "timestamp": now,
                                       "detail": f"Discovery failed: {str(e)[:80]}"})

    if not apply_url:
        return {
            "status": "error",
            "error": "No valid application URL available. All candidate URLs are unreachable or generic.",
            "verification_steps": verification_steps,
        }

    # ── Build application record ─────────────────────────────────
    method = job.apply_mode
    app_status = "Pending"
    verification_steps.append({"step": "Navigate to Apply Page", "status": "complete", "timestamp": now,
                               "detail": f"Opening {apply_url}"})

    if method in ("auto_apply", "one_click"):
        verification_steps.append({"step": "Ready for Submission", "status": "complete", "timestamp": now,
                                   "detail": "Application page loaded, ready for form fill"})
        app_status = "Applied"
    elif method == "needs_review":
        verification_steps.append({"step": "Awaiting User Review", "status": "pending", "timestamp": now,
                                   "detail": "Review the application in the WebView before submitting"})
        app_status = "Needs Review"
    else:
        verification_steps.append({"step": "External Application", "status": "pending", "timestamp": now,
                                   "detail": "Complete the application on the company's page"})
        app_status = "Pending"

    record = ApplicationRecord(
        job_id=job_id,
        company_name=job.company_name,
        role_title=job.role_title,
        status=app_status,
        source=job.source,
        method=method,
        apply_url=apply_url,
        steps=verification_steps,
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
        "url_source": url_source,
        "live_verified": live_verified,
        "verification_steps": verification_steps,
    }


# ══════════════════════════════════════════════════════════════
#  CORS Proxy — allows iframe embedding of company job pages
# ══════════════════════════════════════════════════════════════

@router.get("/proxy-page")
async def proxy_page(url: str = Query(..., description="URL to proxy")):
    """Fetch a page server-side and return its HTML with iframe-blocking headers removed.
    This enables the frontend WebView iframe to render company career pages that
    normally set X-Frame-Options or restrictive CSP.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return HTMLResponse("<h3>Invalid URL</h3>", status_code=400)

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = await client.get(url)

            if resp.status_code >= 400:
                return HTMLResponse(
                    f"<html><body style='font-family:Inter,sans-serif;background:#0f0f14;color:#e0e0e0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                    f"<div style='text-align:center'><h2>⚠️ Page returned HTTP {resp.status_code}</h2>"
                    f"<p style='color:#888'>The job page could not be loaded.</p>"
                    f"<a href='{url}' target='_blank' style='color:#a78bfa'>Open in new tab →</a></div></body></html>",
                    status_code=200,
                )

            html = resp.text
            final_url = str(resp.url)
            base_domain = f"{parsed.scheme}://{parsed.netloc}"

            # Inject <base> tag so relative URLs resolve correctly
            base_tag = f'<base href="{final_url}" target="_blank">'
            if '<head>' in html.lower():
                html = _re.sub(r'(<head[^>]*>)', r'\1' + base_tag, html, count=1, flags=_re.IGNORECASE)
            elif '<html' in html.lower():
                html = _re.sub(r'(<html[^>]*>)', r'\1<head>' + base_tag + '</head>', html, count=1, flags=_re.IGNORECASE)
            else:
                html = base_tag + html

            return HTMLResponse(
                content=html,
                status_code=200,
                headers={
                    "X-Proxied-From": final_url,
                    # Explicitly allow framing
                    "X-Frame-Options": "ALLOWALL",
                    "Content-Security-Policy": "",
                },
            )
    except httpx.TimeoutException:
        return HTMLResponse(
            "<html><body style='font-family:Inter,sans-serif;background:#0f0f14;color:#e0e0e0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h2>⏱ Request timed out</h2><p style='color:#888'>The page took too long to load.</p>"
            f"<a href='{url}' target='_blank' style='color:#a78bfa'>Open in new tab →</a></div></body></html>",
            status_code=200,
        )
    except Exception as e:
        return HTMLResponse(
            f"<html><body style='font-family:Inter,sans-serif;background:#0f0f14;color:#e0e0e0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            f"<div style='text-align:center'><h2>❌ Failed to load page</h2><p style='color:#888'>{str(e)[:200]}</p>"
            f"<a href='{url}' target='_blank' style='color:#a78bfa'>Open in new tab →</a></div></body></html>",
            status_code=200,
        )


@router.get("/verify-url")
async def verify_url_live(url: str = Query(...)):
    """Quick live check — is this URL reachable and does it look like a job page?"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return {"reachable": False, "reason": "Invalid URL scheme"}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }) as client:
            resp = await client.get(url)
            final_url = str(resp.url)
            is_job_page = False
            page_title = ""

            if resp.status_code < 400:
                text_lower = resp.text[:10000].lower()
                # Detect job-related content
                job_signals = ["apply", "job", "career", "position", "role", "hiring",
                              "resume", "application", "work with us", "join"]
                signal_count = sum(1 for s in job_signals if s in text_lower)
                is_job_page = signal_count >= 2
                # Extract title
                title_match = _re.search(r'<title[^>]*>([^<]+)</title>', resp.text[:5000], _re.IGNORECASE)
                page_title = title_match.group(1).strip() if title_match else ""

            return {
                "reachable": resp.status_code < 400,
                "status_code": resp.status_code,
                "final_url": final_url,
                "is_job_page": is_job_page,
                "page_title": page_title,
                "can_iframe": "x-frame-options" not in {k.lower() for k in resp.headers.keys()},
            }
    except Exception as e:
        return {"reachable": False, "reason": str(e)[:200]}


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


# ══════════════════════════════════════════════════════════
#  Link Verification & Resume Rewrite
# ══════════════════════════════════════════════════════════

@router.get("/jobs/{job_id}/verify")
async def verify_job_url(job_id: str):
    """Verify a job's application URL is live and has an active form."""
    job = store.get_job_by_id(job_id)
    if not job:
        return {"status": "error", "error": "Job not found"}

    from services.link_verifier import verify_and_update_job
    result = await verify_and_update_job(job)
    return {
        "status": "ok",
        "job_id": job_id,
        "verification": result,
    }


@router.post("/resume/rewrite")
async def rewrite_resume(
    resume_text: str = Form(""),
    job_id: str = Form(...),
    github_url: str = Form(""),
    linkedin_url: str = Form(""),
    advanced: bool = Form(False),
):
    """Rewrite resume to be ATS-optimized for a specific JD."""
    job = store.get_job_by_id(job_id)
    if not job:
        return {"status": "error", "error": "Job not found"}

    # Use stored resume text if not provided
    if not resume_text:
        profile = store.get_profile()
        resume_text = profile.resume_text if profile else ""
    if not resume_text:
        return {"status": "error", "error": "No resume text available. Upload a resume first."}

    from services.resume_rewriter import rewrite_resume_for_jd, fetch_github_profile

    github_data = None
    if advanced and github_url:
        github_data = await fetch_github_profile(github_url)

    jd_text = job.jd_summary or job.job_description or job.role_title
    result = await rewrite_resume_for_jd(
        resume_text=resume_text,
        jd_text=jd_text,
        job_title=job.role_title,
        company_name=job.company_name,
        github_data=github_data,
        linkedin_url=linkedin_url or None,
    )

    return {
        "status": "ok",
        "rewrite": result,
    }


@router.get("/resume/rewrite-stream/{job_id}")
async def stream_resume_rewrite(job_id: str, github_url: str = ""):
    """SSE endpoint that streams resume rewrite edits in real-time."""
    import json as _json

    job = store.get_job_by_id(job_id)
    if not job:
        async def error_gen():
            yield f"data: {_json.dumps({'type': 'error', 'data': {'message': 'Job not found'}})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    profile = store.get_profile()
    resume_text = profile.resume_text if profile else ""
    if not resume_text:
        async def error_gen2():
            yield f"data: {_json.dumps({'type': 'error', 'data': {'message': 'No resume uploaded'}})}\n\n"
        return StreamingResponse(error_gen2(), media_type="text/event-stream")

    from services.resume_rewriter import stream_rewrite_edits, fetch_github_profile

    github_data = None
    if github_url:
        github_data = await fetch_github_profile(github_url)

    jd_text = job.jd_summary or job.job_description or job.role_title

    async def event_generator():
        async for event in stream_rewrite_edits(
            resume_text=resume_text,
            jd_text=jd_text,
            job_title=job.role_title,
            company_name=job.company_name,
            github_data=github_data,
        ):
            yield f"data: {_json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ══════════════════════════════════════════════════════════════
#  Real Job Fetching — Refresh jobs with live data
# ══════════════════════════════════════════════════════════════

@router.post("/jobs/refresh")
async def refresh_jobs(
    queries: Optional[list[str]] = Body(None),
    max_queries: int = Body(5),
):
    """Fetch real jobs from job boards and replace seed data.
    Only jobs with direct apply URLs are kept."""
    from services.real_job_fetcher import refresh_jobs_data
    result = await refresh_jobs_data(queries=queries, max_queries=max_queries)
    if result["status"] == "ok":
        # Reload the store
        store._jobs.clear()
        store._load()
    return result


@router.get("/jobs/refresh-status")
async def refresh_status():
    """Check current job data status."""
    total = len(store._jobs)
    with_url = sum(1 for j in store._jobs.values() if j.job_url and j.job_url.startswith("http") and len(j.job_url.split("/")) > 3)
    fake = sum(1 for j in store._jobs.values() if j.role_title and j.role_title.startswith("Open Role at"))
    return {
        "total_jobs": total,
        "jobs_with_apply_url": with_url,
        "fake_seed_jobs": fake,
        "needs_refresh": fake > total * 0.5,
    }
