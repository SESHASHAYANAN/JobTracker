"""API response parsers for Greenhouse, Ashby, and Lever.

Direct port of career-ops scan.mjs parseGreenhouse/parseAshby/parseLever.
"""
from __future__ import annotations

from agents.models import ScannedJob


def parse_greenhouse(json_data: dict, company_name: str) -> list[ScannedJob]:
    """Parse Greenhouse API response into ScannedJob objects.

    Greenhouse API: boards-api.greenhouse.io/v1/boards/{slug}/jobs
    Response: {"jobs": [{"title": str, "absolute_url": str, "location": {"name": str}}]}
    """
    jobs_data = json_data.get("jobs", [])
    results = []
    for j in jobs_data:
        results.append(ScannedJob(
            title=j.get("title", ""),
            url=j.get("absolute_url", ""),
            company=company_name,
            location=j.get("location", {}).get("name", "") if isinstance(j.get("location"), dict) else "",
        ))
    return results


def parse_ashby(json_data: dict, company_name: str) -> list[ScannedJob]:
    """Parse Ashby API response into ScannedJob objects.

    Ashby API: api.ashbyhq.com/posting-api/job-board/{slug}
    Response: {"jobs": [{"title": str, "jobUrl": str, "location": str}]}
    """
    jobs_data = json_data.get("jobs", [])
    results = []
    for j in jobs_data:
        results.append(ScannedJob(
            title=j.get("title", ""),
            url=j.get("jobUrl", ""),
            company=company_name,
            location=j.get("location", ""),
        ))
    return results


def parse_lever(json_data, company_name: str) -> list[ScannedJob]:
    """Parse Lever API response into ScannedJob objects.

    Lever API: api.lever.co/v0/postings/{slug}
    Response: [{"text": str, "hostedUrl": str, "categories": {"location": str}}]
    """
    if not isinstance(json_data, list):
        return []
    results = []
    for j in json_data:
        location = ""
        cats = j.get("categories", {})
        if isinstance(cats, dict):
            location = cats.get("location", "")
        results.append(ScannedJob(
            title=j.get("text", ""),
            url=j.get("hostedUrl", ""),
            company=company_name,
            location=location,
        ))
    return results


# Parser registry — maps API type to parser function
PARSERS = {
    "greenhouse": parse_greenhouse,
    "ashby": parse_ashby,
    "lever": parse_lever,
}
