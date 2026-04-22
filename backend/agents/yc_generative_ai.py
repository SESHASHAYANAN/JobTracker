"""YC Generative AI Tag Agent — prioritises Gen AI startups."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get

TAG_URL = "https://yc-oss.github.io/api/tags/generative-ai.json"


async def fetch_yc_generative_ai() -> list[Job]:
    data = await safe_get(TAG_URL, json_response=True)
    jobs: list[Job] = []
    if not data or not isinstance(data, list):
        print("[yc_gen_ai] No data or unexpected format")
        return jobs

    for c in data:
        name = c.get("name", "")
        if not name:
            continue
        slug = c.get("slug", "") or name.lower().replace(" ", "-")
        website = c.get("website", "") or c.get("url", "") or ""
        batch = c.get("batch", "") or ""
        one_liner = c.get("one_liner", "") or c.get("description", "") or ""

        founders = []
        for f in c.get("founders", []) or []:
            from models import Founder
            founders.append(Founder(
                name=f.get("name", ""),
                title=f.get("title", "") or "Founder",
                linkedin=f.get("linkedin", ""),
                twitter=f.get("twitter", ""),
                source="yc_gen_ai_tag",
            ))

        job = Job(
            company_name=name,
            company_website=website,
            company_slug=slug,
            batch=batch,
            stage=c.get("stage", ""),
            team_size=c.get("team_size", 0) or 0,
            status="active",
            is_hiring=True,
            role_title=f"Open Role at {name}",
            country=c.get("country", "") or c.get("location", ""),
            job_url=c.get("jobs_url", "") or website,
            job_description=one_liner,
            jd_summary=one_liner[:300],
            source="yc_generative_ai_tag",
            founders=founders,
            industry_tags=["Generative AI"],
            relevance_score=0.85,
            vc_backers=["Y Combinator"],
        )
        job.generate_id()
        jobs.append(job)

    print(f"[yc_gen_ai] Fetched {len(jobs)} generative AI companies")
    return jobs
