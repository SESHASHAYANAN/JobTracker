"""Agent Coordinator — launches all agents, normalises, deduplicates, scores, and stores."""
from __future__ import annotations
import asyncio
import traceback
from models import Job
from store import store
from services.gemini_service import summarise_jd, infer_job_fields

# Import all agents
from agents.yc_oss_api import fetch_yc_oss_hiring
from agents.yc_generative_ai import fetch_yc_generative_ai
from agents.yc_workatastartup import fetch_workatastartup
from agents.jobspy_agent import fetch_jobspy_jobs
from agents.browse_ai_vc import fetch_browse_ai_vc_portfolio
from agents.browse_ai_boards import fetch_browse_ai_boards
from agents.hn_hiring import fetch_hn_hiring
from agents.remote_boards import fetch_remote_boards
from agents.github_hiring import fetch_github_hiring
from agents.twitter_hiring import fetch_twitter_hiring
from agents.funding_news import fetch_funding_news_careers
from agents.startup_directories import fetch_startup_directories
from agents.playwright_wellfound import fetch_wellfound_jobs
from agents.apimart_enrichment import enrich_jobs_with_apimart
from agents.founder_discovery import discover_founders
from agents.diverse_seed import get_diverse_seed_jobs
from agents.diverse_seed_extra import get_extra_seed_jobs
from services.startup_seed import get_startup_seed_jobs
from services.startup_classifier import classify_and_enrich, compute_startup_rank


async def _run_agent(name: str, coro):
    """Run a single agent with error handling."""
    try:
        result = await coro
        store.mark_crawl(name)
        print(f"[coordinator] OK {name} returned {len(result)} results")
        return result
    except Exception as e:
        print(f"[coordinator] ERR {name} failed: {e}")
        traceback.print_exc()
        return []


async def run_all_agents():
    """Launch all scraping agents in parallel, then enrich and store."""
    print("[coordinator] Starting all agents...")

    # Phase 1: Primary data collection (parallel)
    results = await asyncio.gather(
        _run_agent("yc_oss_api", fetch_yc_oss_hiring()),
        _run_agent("yc_generative_ai", fetch_yc_generative_ai()),
        _run_agent("yc_workatastartup", fetch_workatastartup()),
        _run_agent("jobspy", fetch_jobspy_jobs()),
        _run_agent("browse_ai_vc", fetch_browse_ai_vc_portfolio()),
        _run_agent("browse_ai_boards", fetch_browse_ai_boards()),
        _run_agent("hn_hiring", fetch_hn_hiring()),
        _run_agent("remote_boards", fetch_remote_boards()),
        _run_agent("github_hiring", fetch_github_hiring()),
        _run_agent("twitter_hiring", fetch_twitter_hiring()),
        _run_agent("funding_news", fetch_funding_news_careers()),
        _run_agent("startup_directories", fetch_startup_directories()),
        _run_agent("wellfound", fetch_wellfound_jobs()),
        return_exceptions=True,
    )

    # Flatten results
    all_jobs: list[Job] = []
    for r in results:
        if isinstance(r, list):
            all_jobs.extend(r)

    # Phase 1b: Add diverse seed data (curated VC portfolio companies)
    seed_jobs = get_diverse_seed_jobs()
    all_jobs.extend(seed_jobs)
    print(f"[coordinator] Added {len(seed_jobs)} curated diverse startup jobs")

    extra_seed_jobs = get_extra_seed_jobs()
    all_jobs.extend(extra_seed_jobs)
    print(f"[coordinator] Added {len(extra_seed_jobs)} extra diverse startup jobs")

    # Phase 1c: Indian startup engineering seed
    try:
        startup_seed_jobs = get_startup_seed_jobs()
        all_jobs.extend(startup_seed_jobs)
        print(f"[coordinator] Added {len(startup_seed_jobs)} Indian startup engineering jobs")
    except Exception as e:
        print(f"[coordinator] startup_seed failed: {e}")

    print(f"[coordinator] Collected {len(all_jobs)} raw jobs from all agents")

    # IMMEDIATELY score and store so the API has data right away
    for job in all_jobs:
        job.relevance_score = _compute_score(job)
        if not job.id:
            job.generate_id()
    store.add_jobs(all_jobs)
    print(f"[coordinator] OK Initial store: {store.count} active jobs available immediately")

    # Phase 2: Enrichment (runs in background, re-stores enriched data)
    print("[coordinator] Running enrichment (background)...")
    try:
        all_jobs = await enrich_jobs_with_apimart(all_jobs)
    except Exception as e:
        print(f"[coordinator] apimart enrichment failed: {e}")

    # Phase 3: Founder discovery
    print("[coordinator] Running founder discovery...")
    try:
        all_jobs = await discover_founders(all_jobs)
    except Exception as e:
        print(f"[coordinator] Founder discovery failed: {e}")

    # Phase 4: Gemini enrichment (JD summaries + field inference for top jobs)
    print("[coordinator] Running Gemini enrichment...")
    enriched_count = 0
    for job in all_jobs[:30]:  # limit to avoid rate limits
        try:
            if job.job_description and not job.jd_summary:
                job.jd_summary = await summarise_jd(job.job_description)
                enriched_count += 1
            if job.job_description and (not job.visa_sponsorship or not job.experience_level):
                fields = await infer_job_fields(job.job_description, job.role_title)
                if fields:
                    if not job.visa_sponsorship:
                        job.visa_sponsorship = fields.get("visa_sponsorship", "Unknown")
                    if not job.experience_level:
                        job.experience_level = fields.get("experience_level", "")
                    if not job.salary_range:
                        job.salary_range = fields.get("salary_range", "")
                    if not job.work_type:
                        job.work_type = fields.get("work_type", "")
                    if not job.role_category:
                        job.role_category = fields.get("role_category", "")
                    if fields.get("industry_tags"):
                        job.industry_tags = list(set(job.industry_tags + fields["industry_tags"]))
        except Exception as e:
            print(f"[coordinator] Gemini enrichment skipped for {job.company_name}: {e}")

    print(f"[coordinator] Gemini-enriched {enriched_count} JD summaries")

    # Phase 5: Startup classification and re-ranking
    print("[coordinator] Running startup classification...")
    startup_count = 0
    stealth_count = 0
    for job in all_jobs:
        try:
            classify_and_enrich(job)
            if job.is_startup:
                startup_count += 1
            if job.is_stealth:
                stealth_count += 1
        except Exception:
            pass
    print(f"[coordinator] Classified {startup_count} startups, {stealth_count} stealth")

    # Re-score with startup-aware ranking
    for job in all_jobs:
        job.relevance_score = _compute_score(job)
        # Blend with startup rank
        startup_rank = compute_startup_rank(job)
        job.relevance_score = round(max(job.relevance_score, startup_rank), 2)

    store.add_jobs(all_jobs)
    print(f"[coordinator] OK Final store: {store.count} active jobs after enrichment")


def _compute_score(job: Job) -> float:
    """Compute relevance score based on multiple factors."""
    score = job.relevance_score or 0.3

    # YC or elite VC boost
    elite_vcs = {"y combinator", "a16z", "sequoia", "lightspeed", "bessemer", "founders fund", "pearl"}
    for vc in job.vc_backers:
        if vc.lower() in elite_vcs:
            score += 0.15
            break

    # Batch recency boost
    if job.batch:
        recent_batches = {"w25", "s24", "w24", "s23"}
        if job.batch.lower() in recent_batches:
            score += 0.1

    # Visa boost
    if job.visa_sponsorship and job.visa_sponsorship.lower() == "yes":
        score += 0.05

    # Founder socials boost
    if job.founders:
        has_social = any(f.linkedin or f.twitter for f in job.founders)
        if has_social:
            score += 0.1

    # JD summary present
    if job.jd_summary and len(job.jd_summary) > 20:
        score += 0.05

    return min(score, 1.0)
