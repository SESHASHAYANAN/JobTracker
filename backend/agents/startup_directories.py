"""Startup Directories Agent — crawls directories for job/careers links."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def fetch_startup_directories() -> list[Job]:
    """Crawl startup directories and product sites for job listings."""
    jobs: list[Job] = []
    directories = [
        "https://www.startupjobs.com/api/startup-jobs?limit=25",
    ]
    for url in directories:
        try:
            data = await safe_get(url, json_response=True)
            if data and isinstance(data, list):
                for item in data[:25]:
                    name = item.get("company", "") or item.get("startup", "")
                    if not name:
                        continue
                    slug = name.lower().replace(" ", "-")
                    job = Job(
                        company_name=name,
                        company_slug=slug,
                        role_title=item.get("title", "") or item.get("role", "") or f"Role at {name}",
                        job_url=item.get("url", ""),
                        country=item.get("location", ""),
                        work_type=item.get("type", ""),
                        source="startup_directories",
                        status="active",
                        is_hiring=True,
                        relevance_score=0.4,
                    )
                    job.generate_id()
                    jobs.append(job)
            elif data is None:
                # Try HTML scrape fallback
                html = await safe_get(url.replace("/api/", "/"))
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    for card in soup.select(".job-card, .listing, article")[:20]:
                        title_el = card.select_one("h2, h3, .title")
                        company_el = card.select_one(".company, .org")
                        if title_el and company_el:
                            name = company_el.get_text(strip=True)
                            slug = name.lower().replace(" ", "-")
                            link_el = card.select_one("a[href]")
                            job = Job(
                                company_name=name,
                                company_slug=slug,
                                role_title=title_el.get_text(strip=True),
                                job_url=link_el.get("href", "") if link_el else "",
                                source="startup_directories",
                                status="active",
                                is_hiring=True,
                                relevance_score=0.35,
                            )
                            job.generate_id()
                            jobs.append(job)
        except Exception as e:
            print(f"[startup_dirs] Error: {e}")

    print(f"[startup_dirs] Found {len(jobs)} directory listings")
    return jobs
