"""GitHub Org Hiring Agent — scans org READMEs for hiring signals."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get


async def fetch_github_hiring() -> list[Job]:
    """Search GitHub for startup orgs with hiring signals."""
    jobs: list[Job] = []
    search_url = (
        "https://api.github.com/search/repositories?"
        "q=%22we+are+hiring%22+in:readme&sort=updated&per_page=20"
    )
    try:
        data = await safe_get(search_url, json_response=True)
        if not data or "items" not in data:
            return jobs
        for repo in data["items"][:20]:
            owner = repo.get("owner", {})
            org_name = owner.get("login", "")
            full_name = repo.get("full_name", "")
            desc = repo.get("description", "") or ""
            html_url = repo.get("html_url", "")
            homepage = repo.get("homepage", "") or ""

            if not org_name:
                continue

            job = Job(
                company_name=org_name,
                company_slug=org_name.lower().replace(" ", "-"),
                company_website=homepage or html_url,
                role_title=f"Engineering Role at {org_name}",
                job_url=homepage or html_url,
                job_description=desc[:500],
                source="github_hiring",
                status="active",
                is_hiring=True,
                relevance_score=0.4,
            )
            job.generate_id()
            jobs.append(job)
    except Exception as e:
        print(f"[github_hiring] Error: {e}")

    print(f"[github_hiring] Found {len(jobs)} repos with hiring signals")
    return jobs
