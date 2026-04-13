"""apimart.ai GPT-4o Enrichment Agent — enriches companies with missing metadata."""
from __future__ import annotations
from models import Job
from services.apimart_service import enrich_company


async def enrich_jobs_with_apimart(jobs: list[Job]) -> list[Job]:
    """Enrich a batch of jobs with GPT-4o via apimart.ai for missing fields.
    Returns the FULL list with enrichments applied in-place to qualifying jobs."""
    # Only enrich jobs missing key fields, and limit batch size
    to_enrich = [j for j in jobs if not j.role_category or not j.industry_tags][:20]
    count = 0

    for job in to_enrich:
        try:
            context = f"{job.job_description or ''} {job.company_name} {job.role_title}"
            data = await enrich_company(job.company_name, context[:2000])
            if data:
                if data.get("industry_tags"):
                    job.industry_tags = list(set(job.industry_tags + data["industry_tags"]))
                if data.get("stage") and data["stage"] != "Unknown" and not job.stage:
                    job.stage = data["stage"]
                if data.get("role_category") and data["role_category"] != "Other":
                    job.role_category = data["role_category"]
                if data.get("work_type") and data["work_type"] != "Unknown" and not job.work_type:
                    job.work_type = data["work_type"]
                if data.get("team_size_bucket") and data["team_size_bucket"] != "Unknown" and not job.team_size:
                    buckets = {"1-10": 5, "10-50": 25, "50-200": 100, "200+": 300}
                    job.team_size = buckets.get(data["team_size_bucket"], 0)
                count += 1
        except Exception as e:
            print(f"[apimart_enrich] Error for {job.company_name}: {e}")

    print(f"[apimart_enrich] Enriched {count} of {len(jobs)} jobs")
    return jobs  # Return ALL jobs, not just enriched subset
