"""JobSpy Multi-board Agent — scrapes LinkedIn, Indeed, Glassdoor, etc."""
from __future__ import annotations
import asyncio
from models import Job
try:
    from jobspy import scrape_jobs
    HAS_JOBSPY = True
except ImportError:
    HAS_JOBSPY = False

SEARCH_TERMS = [
    "startup software engineer",
    "AI ML engineer startup",
    "startup product manager",
    "YC startup hiring",
    "series A startup engineer",
]
COUNTRIES = ["USA", "UK", "Canada", "India", "Remote"]


async def fetch_jobspy_jobs() -> list[Job]:
    """Use JobSpy to scrape multiple job boards."""
    if not HAS_JOBSPY:
        print("[jobspy] JobSpy not installed, skipping")
        return []
    jobs: list[Job] = []
    loop = asyncio.get_event_loop()

    for term in SEARCH_TERMS[:3]:  # limit to avoid rate limiting
        try:
            df = await loop.run_in_executor(
                None,
                lambda t=term: scrape_jobs(
                    site_name=["indeed", "glassdoor"],
                    search_term=t,
                    results_wanted=15,
                    country_indeed="USA",
                )
            )
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    job = Job(
                        company_name=str(row.get("company", "")),
                        company_slug=str(row.get("company", "")).lower().replace(" ", "-"),
                        role_title=str(row.get("title", "")),
                        salary_range=_format_salary(row),
                        work_type=str(row.get("job_type", "")) or "Unknown",
                        country=str(row.get("country", "USA")),
                        city=str(row.get("location", "")),
                        job_url=str(row.get("job_url", "")),
                        job_description=str(row.get("description", ""))[:2000],
                        source="jobspy",
                        status="active",
                        is_hiring=True,
                        relevance_score=0.5,
                    )
                    job.generate_id()
                    jobs.append(job)
        except Exception as e:
            print(f"[jobspy] Error for '{term}': {e}")
            continue

    print(f"[jobspy] Fetched {len(jobs)} jobs")
    return jobs


def _format_salary(row) -> str:
    min_s = row.get("min_amount", "")
    max_s = row.get("max_amount", "")
    if min_s and max_s:
        return f"${min_s:,.0f} - ${max_s:,.0f}"
    elif min_s:
        return f"${min_s:,.0f}+"
    return ""
