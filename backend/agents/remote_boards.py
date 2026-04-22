"""Remote Job Boards Agent — scrapes RemoteOK, WeWorkRemotely."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from bs4 import BeautifulSoup


async def fetch_remote_boards() -> list[Job]:
    """Scrape remote-first startup job boards."""
    jobs: list[Job] = []
    # ── RemoteOK (has a JSON API) ──
    try:
        data = await safe_get("https://remoteok.com/api", json_response=True)
        if data and isinstance(data, list):
            for item in data[1:40]:  # skip header, limit
                company = item.get("company", "")
                if not company:
                    continue
                slug = company.lower().replace(" ", "-")
                tags = item.get("tags", []) or []

                job = Job(
                    company_name=company,
                    company_slug=slug,
                    company_website=item.get("company_logo", ""),
                    role_title=item.get("position", ""),
                    salary_range=_remote_ok_salary(item),
                    work_type="remote",
                    country="Remote",
                    job_url=item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                    job_description=item.get("description", "")[:1500],
                    source="remoteok",
                    status="active",
                    is_hiring=True,
                    industry_tags=tags,
                    relevance_score=0.45,
                )
                job.generate_id()
                jobs.append(job)
    except Exception as e:
        print(f"[remote_boards] RemoteOK error: {e}")

    # ── WeWorkRemotely (HTML scrape) ──
    try:
        html = await safe_get("https://weworkremotely.com/remote-jobs/search?utf8=%E2%9C%93&term=startup")
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for li in soup.select("li.feature")[:20]:
                link = li.select_one("a")
                if not link:
                    continue
                title_el = li.select_one(".title")
                company_el = li.select_one(".company")
                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                if not company:
                    continue
                slug = company.lower().replace(" ", "-")
                href = link.get("href", "")
                job_url = f"https://weworkremotely.com{href}" if href.startswith("/") else href

                job = Job(
                    company_name=company,
                    company_slug=slug,
                    role_title=title,
                    work_type="remote",
                    country="Remote",
                    job_url=job_url,
                    source="weworkremotely",
                    status="active",
                    is_hiring=True,
                    relevance_score=0.45,
                )
                job.generate_id()
                jobs.append(job)
    except Exception as e:
        print(f"[remote_boards] WWR error: {e}")

    print(f"[remote_boards] Fetched {len(jobs)} remote jobs")
    return jobs


def _remote_ok_salary(item: dict) -> str:
    mn = item.get("salary_min", "")
    mx = item.get("salary_max", "")
    if mn and mx:
        return f"${int(mn):,} - ${int(mx):,}"
    return ""
