"""YC OSS API Agent — fetches hiring.json, all.json, and tag endpoints."""
from __future__ import annotations
import asyncio
from models import Job, Founder
from services.antiblock import safe_get

YC_BASE = "https://yc-oss.github.io/api"


async def fetch_yc_oss_hiring() -> list[Job]:
    """Pull hiring.json and all.json from YC OSS API."""
    jobs: list[Job] = []
    hiring_data = await safe_get(f"{YC_BASE}/companies/hiring.json", json_response=True)
    all_data = await safe_get(f"{YC_BASE}/companies/all.json", json_response=True)

    companies = {}
    if all_data and isinstance(all_data, list):
        for c in all_data:
            slug = c.get("slug", "") or c.get("id", "")
            if slug:
                companies[slug] = c

    if hiring_data and isinstance(hiring_data, list):
        for company in hiring_data:
            slug = company.get("slug", "") or company.get("id", "")
            # merge with all_data details
            full = {**companies.get(slug, {}), **company}
            job = _parse_yc_company(full)
            if job:
                jobs.append(job)

    # also parse remaining from all_data that are hiring
    if all_data and isinstance(all_data, list):
        existing_slugs = {j.company_slug for j in jobs}
        for c in all_data:
            slug = c.get("slug", "") or c.get("id", "")
            if slug in existing_slugs:
                continue
            if c.get("is_hiring") or c.get("isHiring"):
                job = _parse_yc_company(c)
                if job:
                    jobs.append(job)

    print(f"[yc_oss_api] Fetched {len(jobs)} companies")
    return jobs


def _parse_yc_company(c: dict) -> Job | None:
    name = c.get("name", "")
    if not name:
        return None
    slug = c.get("slug", "") or c.get("id", "") or name.lower().replace(" ", "-")
    batch = c.get("batch", "") or c.get("batch_name", "")
    stage = c.get("stage", "") or c.get("subindustry", "")
    team_size = c.get("team_size", 0) or c.get("teamSize", 0)
    if isinstance(team_size, str):
        try:
            team_size = int(team_size.split("-")[0]) if "-" in team_size else int(team_size)
        except ValueError:
            team_size = 0

    tags = c.get("tags", []) or c.get("industries", []) or []
    if isinstance(tags, str):
        tags = [tags]

    # extract founders
    founders = []
    for f in c.get("founders", []) or []:
        founders.append(Founder(
            name=f.get("name", "") or f.get("full_name", ""),
            title=f.get("title", "") or "Founder",
            linkedin=f.get("linkedin", "") or f.get("linkedin_url", ""),
            twitter=f.get("twitter", "") or f.get("twitter_url", ""),
            email=f.get("email", ""),
            source="yc_oss_api",
        ))

    website = c.get("website", "") or c.get("url", "") or ""
    one_liner = c.get("one_liner", "") or c.get("description", "") or c.get("long_description", "") or ""

    job = Job(
        company_name=name,
        company_website=website,
        company_slug=slug,
        batch=batch,
        stage=stage if stage else None,
        team_size=team_size if team_size else None,
        founded_year=c.get("founded_year") or c.get("year_founded"),
        funding_total=c.get("funding", "") or c.get("funding_total", ""),
        status="active" if c.get("status", "Active") in ("Active", "active", None, "") else "inactive",
        is_hiring=bool(c.get("is_hiring", True) or c.get("isHiring", True)),
        role_title=c.get("role", "") or c.get("job_title", "") or f"Open Role at {name}",
        role_category=c.get("role_category", ""),
        country=c.get("country", "") or c.get("location", ""),
        city=c.get("city", ""),
        job_url=c.get("jobs_url", "") or c.get("careers_url", "") or website,
        job_description=one_liner,
        jd_summary=one_liner[:300] if one_liner else "",
        source="yc_oss_api",
        founders=founders,
        industry_tags=tags,
        relevance_score=0.7 if batch else 0.4,
        vc_backers=["Y Combinator"],
    )
    job.generate_id()
    return job
