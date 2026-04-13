"""LinkedIn Company Careers Agent — parse public LinkedIn company job pages."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def fetch_linkedin_careers(company_names: list[str]) -> list[Job]:
    """Open public LinkedIn company job pages and parse listings."""
    jobs: list[Job] = []
    for name in company_names[:10]:
        slug = name.lower().replace(" ", "-").replace(".", "")
        url = f"https://www.linkedin.com/company/{slug}/jobs/"
        try:
            html = await safe_get(url, timeout=15)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            # LinkedIn public pages often block, but try
            cards = soup.select(".base-card, .job-result-card")[:5]
            for card in cards:
                title_el = card.select_one(".base-card__title, h3")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = card.select_one("a[href]")
                loc_el = card.select_one(".job-result-card__location")

                job = Job(
                    company_name=name,
                    company_slug=slug,
                    role_title=title,
                    country=loc_el.get_text(strip=True) if loc_el else "",
                    job_url=link_el.get("href", "") if link_el else "",
                    source="linkedin_careers",
                    status="active",
                    is_hiring=True,
                    relevance_score=0.5,
                )
                job.generate_id()
                jobs.append(job)
        except Exception as e:
            print(f"[linkedin_careers] Error for {name}: {e}")

    print(f"[linkedin_careers] Found {len(jobs)} LinkedIn listings")
    return jobs
