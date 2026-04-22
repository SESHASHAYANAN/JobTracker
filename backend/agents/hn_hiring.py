"""HN 'Who is Hiring' Agent — scrapes latest HN hiring threads."""
from __future__ import annotations
from models import Job
from services.antiblock import safe_get
from services.gemini_service import parse_hn_post
from bs4 import BeautifulSoup

HN_SEARCH = "https://hn.algolia.com/api/v1/search?query=who+is+hiring&tags=ask_hn&hitsPerPage=3"


async def fetch_hn_hiring() -> list[Job]:
    """Parse latest HN 'Who is Hiring' thread posts."""
    jobs: list[Job] = []
    try:
        data = await safe_get(HN_SEARCH, json_response=True)
        if not data or not data.get("hits"):
            print("[hn_hiring] No HN threads found")
            return jobs

        # get the latest thread
        latest = data["hits"][0]
        thread_id = latest.get("objectID", "")
        if not thread_id:
            return jobs

        # fetch comments
        comments_url = f"https://hn.algolia.com/api/v1/items/{thread_id}"
        thread_data = await safe_get(comments_url, json_response=True)
        if not thread_data:
            return jobs

        children = thread_data.get("children", [])[:50]  # limit
        for comment in children:
            text = comment.get("text", "")
            if not text or len(text) < 30:
                continue

            # Strip HTML
            soup = BeautifulSoup(text, "html.parser")
            clean_text = soup.get_text(separator=" ").strip()

            # Try to parse with Gemini
            parsed = await parse_hn_post(clean_text)
            if not parsed:
                continue

            name = parsed.get("company_name", "")
            if not name:
                continue
            slug = name.lower().replace(" ", "-")

            job = Job(
                company_name=name,
                company_slug=slug,
                role_title=parsed.get("role_title", "") or f"Role at {name}",
                salary_range=parsed.get("salary_range", ""),
                visa_sponsorship=parsed.get("visa_sponsorship", ""),
                work_type=parsed.get("work_type", ""),
                country=parsed.get("location", ""),
                job_url=parsed.get("job_url", "") or f"https://news.ycombinator.com/item?id={comment.get('id', '')}",
                job_description=clean_text[:1500],
                source="hn_hiring",
                status="active",
                is_hiring=True,
                relevance_score=0.6,
            )
            job.generate_id()
            jobs.append(job)

    except Exception as e:
        print(f"[hn_hiring] Error: {e}")

    print(f"[hn_hiring] Parsed {len(jobs)} jobs from HN")
    return jobs
