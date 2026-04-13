"""YC WorkAtAStartup Agent — scrapes workatastartup.com via ycombinator-scraper or direct API."""
from __future__ import annotations
from models import Job, Founder
from services.antiblock import safe_get

WAAS_API = "https://www.workatastartup.com/companies/api"


async def fetch_workatastartup() -> list[Job]:
    """Scrape WorkAtAStartup listings."""
    jobs: list[Job] = []
    try:
        # WorkAtAStartup has a public API endpoint
        data = await safe_get(f"{WAAS_API}?page=1", json_response=True)
        if not data:
            # try alternative format
            data = await safe_get("https://www.workatastartup.com/companies.json", json_response=True)
        if not data:
            print("[waas] Could not fetch data")
            return jobs

        companies = data if isinstance(data, list) else data.get("companies", []) if isinstance(data, dict) else []
        for c in companies[:100]:  # limit to keep it reasonable
            name = c.get("name", "")
            if not name:
                continue
            slug = c.get("slug", "") or name.lower().replace(" ", "-")

            founders = []
            for f in c.get("founders", []) or c.get("team", []) or []:
                founders.append(Founder(
                    name=f.get("name", "") or f.get("full_name", ""),
                    title=f.get("title", "") or "Founder",
                    linkedin=f.get("linkedin_url", "") or f.get("linkedin", ""),
                    twitter=f.get("twitter_url", "") or f.get("twitter", ""),
                    email=f.get("email", ""),
                    source="workatastartup",
                ))

            for role in c.get("jobs", []) or [{"title": f"Open Role at {name}"}]:
                job = Job(
                    company_name=name,
                    company_website=c.get("website", ""),
                    company_slug=slug,
                    batch=c.get("batch", ""),
                    stage=c.get("stage", ""),
                    team_size=c.get("team_size", 0),
                    founded_year=c.get("year_founded"),
                    status="active",
                    is_hiring=True,
                    role_title=role.get("title", "") or role.get("role", "") or f"Open Role at {name}",
                    experience_level=role.get("experience", ""),
                    visa_sponsorship=role.get("visa", "Unknown"),
                    salary_range=role.get("salary", ""),
                    work_type=role.get("remote", ""),
                    country=role.get("location", "") or c.get("location", ""),
                    job_url=role.get("url", "") or c.get("website", ""),
                    job_description=role.get("description", "") or c.get("one_liner", ""),
                    source="workatastartup",
                    founders=founders,
                    relevance_score=0.75,
                    vc_backers=["Y Combinator"],
                )
                job.generate_id()
                jobs.append(job)
    except Exception as e:
        print(f"[waas] Error: {e}")
    print(f"[waas] Fetched {len(jobs)} jobs")
    return jobs
