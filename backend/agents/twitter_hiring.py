"""Twitter/X Hiring Agent — uses Groq to parse hiring tweets found via public search."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get


async def fetch_twitter_hiring() -> list[Job]:
    """Search public tweet caches/mirrors for startup hiring posts.
    Since Twitter/X API requires paid access, we use Nitter mirrors and public caches."""
    jobs: list[Job] = []
    # Use public Nitter instance search (these may go up/down)
    nitter_urls = [
        "https://nitter.net/search?f=tweets&q=%22we+are+hiring%22+startup&since=",
    ]
    for url in nitter_urls:
        try:
            html = await safe_get(url, timeout=15)
            if not html:
                continue
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            tweets = soup.select(".tweet-body, .timeline-item")[:15]
            for tweet in tweets:
                text_el = tweet.select_one(".tweet-content, .tweet-text")
                if not text_el:
                    continue
                text = text_el.get_text(strip=True)
                if len(text) < 20:
                    continue
                # try to extract company name (first word or @mention)
                words = text.split()
                company = words[0].replace("@", "").replace(":", "") if words else "Unknown"
                job = Job(
                    company_name=company,
                    company_slug=company.lower().replace(" ", "-"),
                    role_title=f"Open Role at {company}",
                    job_description=text[:500],
                    source="twitter_hiring",
                    status="active",
                    is_hiring=True,
                    relevance_score=0.35,
                    work_type="Unknown",
                )
                job.generate_id()
                jobs.append(job)
        except Exception as e:
            print(f"[twitter_hiring] Error: {e}")

    print(f"[twitter_hiring] Found {len(jobs)} hiring tweets")
    return jobs
