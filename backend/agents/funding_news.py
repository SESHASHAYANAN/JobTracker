"""Funding News → Careers Agent — scrapes funding news and resolves career pages."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from services.gemini_service import parse_funding_news


async def fetch_funding_news_careers() -> list[Job]:
    """Scrape recent funding news, extract companies, then find careers pages."""
    jobs: list[Job] = []
    # Use public tech news APIs / feeds
    feeds = [
        "https://hn.algolia.com/api/v1/search?query=startup+funding+series&tags=story&hitsPerPage=15",
    ]
    for feed_url in feeds:
        try:
            data = await safe_get(feed_url, json_response=True)
            if not data or not data.get("hits"):
                continue
            for hit in data["hits"][:10]:
                title = hit.get("title", "")
                url = hit.get("url", "") or hit.get("story_url", "")
                if not title:
                    continue

                # Use Gemini to extract funding info
                parsed = await parse_funding_news(title)
                if not parsed:
                    continue

                for item in parsed[:3]:
                    company = item.get("company", "")
                    if not company:
                        continue
                    slug = company.lower().replace(" ", "-")
                    job = Job(
                        company_name=company,
                        company_slug=slug,
                        company_website=item.get("website", ""),
                        stage=item.get("round", ""),
                        funding_total=item.get("amount", ""),
                        vc_backers=[item.get("lead_vc", "")] if item.get("lead_vc") else [],
                        role_title=f"Open Position at {company}",
                        job_url=item.get("website", "") or url,
                        source="funding_news",
                        status="active",
                        is_hiring=True,
                        relevance_score=0.55,
                    )
                    job.generate_id()
                    jobs.append(job)
        except Exception as e:
            print(f"[funding_news] Error: {e}")

    print(f"[funding_news] Found {len(jobs)} funded startups")
    return jobs
