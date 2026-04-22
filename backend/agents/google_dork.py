"""Google Dork Jobs Agent — searches Google for hiring signals of specific companies."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def fetch_google_dork_jobs(company_names: list[str]) -> list[Job]:
    """Use Google search to find hiring pages for named companies."""
    jobs: list[Job] = []
    for name in company_names[:15]:
        queries = [
            f'"{name}" "we\'re hiring"',
            f'"{name}" careers',
        ]
        for query in queries[:1]:  # limit to 1 query per company
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            try:
                html = await safe_get(url, timeout=15)
                if not html:
                    continue
                soup = BeautifulSoup(html, "html.parser")
                results = soup.select(".result__a")[:3]
                for r in results:
                    href = r.get("href", "")
                    text = r.get_text(strip=True)
                    if href and text:
                        job = Job(
                            company_name=name,
                            company_slug=name.lower().replace(" ", "-"),
                            role_title=text[:100],
                            job_url=href,
                            source="google_dork",
                            status="active",
                            is_hiring=True,
                            relevance_score=0.4,
                        )
                        job.generate_id()
                        jobs.append(job)
            except Exception as e:
                print(f"[google_dork] Error for {name}: {e}")
    print(f"[google_dork] Found {len(jobs)} dork results")
    return jobs
