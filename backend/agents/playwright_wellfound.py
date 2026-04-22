"""Playwright Wellfound Crawler — HTML crawl of wellfound.com/jobs."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def fetch_wellfound_jobs() -> list[Job]:
    """Scrape Wellfound (formerly AngelList Talent) job listings via HTML."""
    jobs: list[Job] = []
    categories = ["software-engineer", "machine-learning", "data-science", "product-manager"]

    for cat in categories[:2]:  # limit to avoid rate limiting
        url = f"https://wellfound.com/role/r/{cat}"
        try:
            html = await safe_get(url, timeout=20)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            # Wellfound uses React SSR, structure varies
            cards = soup.select("[data-test='StartupResult'], .styles_result__rPRNG, .job-listing")[:15]
            for card in cards:
                company_el = card.select_one("h2, .styles_startupName__LhHT2, .company-name")
                title_el = card.select_one("h3, .styles_jobTitle__nMm_9, .job-title")
                salary_el = card.select_one(".styles_salary__il7IK, .salary")
                loc_el = card.select_one(".styles_location__JFdma, .location")

                company = company_el.get_text(strip=True) if company_el else ""
                if not company:
                    continue
                slug = company.lower().replace(" ", "-")
                link_el = card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                job_url = f"https://wellfound.com{href}" if href.startswith("/") else href

                job = Job(
                    company_name=company,
                    company_slug=slug,
                    role_title=title_el.get_text(strip=True) if title_el else cat.replace("-", " ").title(),
                    salary_range=salary_el.get_text(strip=True) if salary_el else "",
                    country=loc_el.get_text(strip=True) if loc_el else "",
                    job_url=job_url,
                    source="wellfound",
                    status="active",
                    is_hiring=True,
                    relevance_score=0.55,
                )
                job.generate_id()
                jobs.append(job)
        except Exception as e:
            print(f"[wellfound] Error for {cat}: {e}")

    print(f"[wellfound] Found {len(jobs)} Wellfound listings")
    return jobs
