"""Company Careers Pattern Agent — probes discovered domains for /careers, /jobs."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup
import re

CAREER_PATHS = ["/careers", "/jobs", "/join-us", "/work-with-us", "/hiring"]


async def fetch_company_careers(domains: list[str]) -> list[Job]:
    """For a list of company domains, probe common career paths and parse listings."""
    jobs: list[Job] = []
    for domain in domains[:30]:  # limit domains to avoid excessive scraping
        domain = domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        for path in CAREER_PATHS:
            url = f"{domain}{path}"
            html = await safe_get(url, timeout=15)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else ""
            if any(kw in title.lower() for kw in ["404", "not found", "error"]):
                continue

            # Extract company name from domain
            company = domain.replace("https://", "").replace("http://", "").replace("www.", "").split(".")[0].title()

            # Look for job listing patterns
            links = soup.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if len(text) < 5 or len(text) > 150:
                    continue
                # heuristic: links with job-like keywords
                if any(kw in href.lower() or kw in text.lower() for kw in ["apply", "position", "role", "job", "opening"]):
                    job_url = href if href.startswith("http") else f"{domain}{href}"
                    job = Job(
                        company_name=company,
                        company_slug=company.lower().replace(" ", "-"),
                        company_website=domain,
                        role_title=text,
                        job_url=job_url,
                        source="company_careers",
                        status="active",
                        is_hiring=True,
                        relevance_score=0.5,
                    )
                    job.generate_id()
                    jobs.append(job)
            if jobs:
                break  # found careers for this domain, move on

    print(f"[company_careers] Found {len(jobs)} career listings")
    return jobs
