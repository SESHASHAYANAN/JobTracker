"""Browse AI VC Portfolio Agent — uses Browse AI robots to scrape VC portfolios (limited to 20 outputs)."""
from __future__ import annotations
import os
from models import Job, Founder
from services.antiblock import safe_get, safe_post
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("BROWSE_AI_API_KEY", "")
ROBOT_ID = os.getenv("BROWSE_AI_ROBOT_ID", "")
BASE = "https://api.browse.ai/v2"


async def fetch_browse_ai_vc_portfolio() -> list[Job]:
    """Fetch VC portfolio companies via Browse AI robots (max 20 outputs)."""
    jobs: list[Job] = []
    if not API_KEY or not ROBOT_ID:
        print("[browse_ai_vc] No API key / robot ID configured")
        return jobs

    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        # Get existing task results
        url = f"{BASE}/robots/{ROBOT_ID}/tasks?page=1"
        data = await safe_get(url, headers=headers, json_response=True)
        if not data:
            print("[browse_ai_vc] No data from Browse AI")
            return jobs

        tasks = data.get("result", {}).get("robotTasks", {}).get("items", [])
        for task in tasks[:20]:  # max 20 outputs
            captured = task.get("capturedData", {}) or {}
            name = captured.get("company_name", "") or captured.get("Company Name", "")
            if not name:
                continue
            slug = name.lower().replace(" ", "-").replace(".", "")
            job = Job(
                company_name=name,
                company_website=captured.get("website", "") or captured.get("Company Website", ""),
                company_slug=slug,
                stage=captured.get("stage", ""),
                role_title=captured.get("role", "") or f"Open Role at {name}",
                country=captured.get("location", ""),
                job_url=captured.get("careers_url", "") or captured.get("website", ""),
                source="browse_ai_vc",
                status="active",
                is_hiring=True,
                relevance_score=0.65,
                vc_backers=[captured.get("vc", "")],
            )
            job.generate_id()
            jobs.append(job)
    except Exception as e:
        print(f"[browse_ai_vc] Error: {e}")

    print(f"[browse_ai_vc] Fetched {len(jobs)} portfolio companies")
    return jobs
