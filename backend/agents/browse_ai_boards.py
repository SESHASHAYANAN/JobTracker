"""Browse AI Startup Job Board Agent — robots for Wellfound, F6S (limited to 20 outputs)."""
from __future__ import annotations
import os
from models import Job
from services.antiblock import safe_get
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("BROWSE_AI_API_KEY", "")
ROBOT_ID = os.getenv("BROWSE_AI_ROBOT_ID", "")
BASE = "https://api.browse.ai/v2"


async def fetch_browse_ai_boards() -> list[Job]:
    """Fetch startup job board listings via Browse AI (max 20)."""
    jobs: list[Job] = []
    if not API_KEY or not ROBOT_ID:
        print("[browse_ai_boards] No credentials")
        return jobs

    headers = {"Authorization": f"Bearer {API_KEY}"}
    try:
        data = await safe_get(
            f"{BASE}/robots/{ROBOT_ID}/tasks?page=1",
            headers=headers,
            json_response=True,
        )
        if not data:
            return jobs

        tasks = data.get("result", {}).get("robotTasks", {}).get("items", [])
        for task in tasks[:20]:
            captured = task.get("capturedData", {}) or {}
            name = captured.get("company_name", "") or captured.get("Company", "")
            role = captured.get("role_title", "") or captured.get("Job Title", "")
            if not name and not role:
                continue
            slug = (name or "unknown").lower().replace(" ", "-")
            job = Job(
                company_name=name or "Unknown",
                company_slug=slug,
                role_title=role or f"Role at {name}",
                salary_range=captured.get("salary", ""),
                work_type=captured.get("work_type", ""),
                country=captured.get("location", ""),
                job_url=captured.get("job_url", ""),
                source="browse_ai_boards",
                status="active",
                is_hiring=True,
                relevance_score=0.55,
            )
            job.generate_id()
            jobs.append(job)
    except Exception as e:
        print(f"[browse_ai_boards] Error: {e}")

    print(f"[browse_ai_boards] Fetched {len(jobs)} board listings")
    return jobs
