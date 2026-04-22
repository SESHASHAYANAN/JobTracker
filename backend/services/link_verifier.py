"""Link Verification Agent — validates job application URLs using Groq/Gemini.

Fetches each link, confirms a live application form exists, validates the
hiring process is open, and cross-checks title/company/location with stored
job data.  Discards any failing link.
"""
from __future__ import annotations
import asyncio
import logging
import re
import os
from typing import Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

# Load .env from project root (two levels up from services/)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(_project_root, '.env'))

logger = logging.getLogger(__name__)

_groq = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
_gemini_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_key:
    genai.configure(api_key=_gemini_key)
_gemini = genai.GenerativeModel("gemini-2.0-flash")

# Common ATS platform markers
ATS_MARKERS = [
    "greenhouse.io", "lever.co", "ashbyhq.com", "workday.com",
    "bamboohr.com", "smartrecruiters.com", "icims.com", "jazz.co",
    "recruitee.com", "workable.com", "breezy.hr", "myworkday",
    "taleo", "jobvite.com", "applytojob.com",
]

# Form indicators in HTML
FORM_INDICATORS = [
    '<form', 'type="file"', 'type="email"', 'apply-form',
    'application-form', 'job-apply', 'submit-application',
    'data-qa="apply"', 'btn-apply', 'apply-button',
    'resume', 'cover letter', 'upload your',
]


async def fetch_page_content(url: str, timeout: float = 15.0) -> tuple[str, int]:
    """Fetch page HTML content. Returns (html, status_code)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        ) as client:
            resp = await client.get(url)
            return resp.text[:15000], resp.status_code  # Limit to 15k chars
    except Exception as e:
        logger.warning(f"[link_verifier] Fetch failed for {url}: {e}")
        return "", 0


def _extract_text_snippet(html: str, max_len: int = 3000) -> str:
    """Extract readable text from HTML for LLM analysis."""
    # Remove scripts and styles
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned[:max_len]


def _has_form_indicators(html: str) -> bool:
    """Quick heuristic check for form elements in HTML."""
    html_lower = html.lower()
    return sum(1 for indicator in FORM_INDICATORS if indicator in html_lower) >= 2


def _is_ats_platform(url: str) -> bool:
    """Check if URL belongs to a known ATS platform."""
    url_lower = url.lower()
    return any(marker in url_lower for marker in ATS_MARKERS)


async def classify_page_with_groq(
    page_text: str, job_title: str, company_name: str, location: str
) -> dict:
    """Use Groq (fast) to classify a fetched page.

    Returns dict with:
      - classification: active_application_form / closed_position / generic_careers_page / unrelated_page
      - has_form: bool
      - title_match: bool
      - company_match: bool
      - location_match: bool
      - confidence: float (0-1)
      - reason: str
    """
    try:
        resp = _groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You classify job application web pages. Respond with ONLY valid JSON, "
                        "no markdown fences. Keys: classification (one of: "
                        "active_application_form, closed_position, generic_careers_page, unrelated_page), "
                        "has_form (bool), title_match (bool - does page mention the expected job title?), "
                        "company_match (bool - does page match the expected company?), "
                        "location_match (bool - does page mention the expected location?), "
                        "confidence (float 0-1), reason (string - brief explanation)."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Classify this page. Expected: '{job_title}' at '{company_name}' "
                        f"in '{location or 'unspecified location'}'.\n\n"
                        f"Page content:\n{page_text[:2500]}"
                    ),
                },
            ],
            max_tokens=300,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        import json
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[link_verifier] Groq classify error: {e}")
        return {
            "classification": "unrelated_page",
            "has_form": False,
            "title_match": False,
            "company_match": False,
            "location_match": False,
            "confidence": 0.0,
            "reason": f"Classification failed: {str(e)[:100]}",
        }


async def find_direct_apply_url(
    company_name: str,
    role_title: str,
    company_website: Optional[str] = None,
    existing_url: Optional[str] = None,
) -> Optional[str]:
    """Use Gemini to find the direct application URL for a job.

    Returns the best candidate URL or None.
    """
    try:
        prompt = (
            "You are a job-search expert. Find the most likely DIRECT application URL "
            "(not a generic careers page) for this position.\n\n"
            f"Company: {company_name}\n"
            f"Role: {role_title}\n"
            f"Company website: {company_website or 'unknown'}\n"
            f"Known URL: {existing_url or 'none'}\n\n"
            "Generate 3-5 candidate URLs that are likely direct application links. "
            "Consider common ATS platforms (Greenhouse, Lever, Ashby, Workday) and "
            "direct careers page patterns.\n\n"
            "Return ONLY a JSON array of URL strings, nothing else. Example:\n"
            '[\"https://jobs.lever.co/company/role-id\", \"https://company.com/careers/apply/role\"]'
        )
        resp = _gemini.generate_content(prompt)
        raw = resp.text.strip() if resp.text else "[]"
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        import json
        urls = json.loads(raw)
        if isinstance(urls, list):
            return urls[0] if urls else None
    except Exception as e:
        logger.error(f"[link_verifier] Gemini URL discovery error: {e}")
    return None


async def verify_application_link(
    url: str,
    job_title: str,
    company_name: str,
    location: str = "",
) -> dict:
    """Verify a single application URL.

    Returns:
      {verified: bool, confidence: float, apply_url: str, reason: str,
       classification: str, cross_check: {title: bool, company: bool, location: bool}}
    """
    result = {
        "verified": False,
        "confidence": 0.0,
        "apply_url": url,
        "reason": "",
        "classification": "unknown",
        "cross_check": {"title": False, "company": False, "location": False},
    }

    if not url:
        result["reason"] = "No URL provided"
        return result

    # Step 1: Fetch the page
    html, status_code = await fetch_page_content(url)
    if status_code == 0 or not html:
        result["reason"] = f"Failed to fetch page (status={status_code})"
        return result

    if status_code >= 400:
        result["reason"] = f"Page returned HTTP {status_code}"
        return result

    # Step 2: Quick heuristic check
    is_ats = _is_ats_platform(url)
    has_forms = _has_form_indicators(html)

    # Step 3: LLM classification
    page_text = _extract_text_snippet(html)
    classification = await classify_page_with_groq(
        page_text, job_title, company_name, location
    )

    result["classification"] = classification.get("classification", "unknown")
    result["cross_check"] = {
        "title": classification.get("title_match", False),
        "company": classification.get("company_match", False),
        "location": classification.get("location_match", True),  # Default true if not specified
    }

    # Step 4: Determine verification
    cls = classification.get("classification", "")
    confidence = classification.get("confidence", 0.0)

    if cls == "active_application_form":
        # Cross-check: at least company OR title must match
        if classification.get("company_match") or classification.get("title_match"):
            result["verified"] = True
            result["confidence"] = confidence
            result["reason"] = classification.get("reason", "Active application form found")
        else:
            result["reason"] = "Application form found but title/company mismatch"
            result["confidence"] = confidence * 0.3
    elif cls == "closed_position":
        result["reason"] = "Position appears to be closed"
        result["confidence"] = confidence
    elif cls == "generic_careers_page":
        result["reason"] = "Generic careers page, not a direct application URL"
        result["confidence"] = confidence
    else:
        result["reason"] = classification.get("reason", "Page does not contain an application form")
        result["confidence"] = confidence

    # Boost confidence for known ATS platforms with form indicators
    if is_ats and has_forms and not result["verified"]:
        result["confidence"] = min(result["confidence"] + 0.2, 1.0)
        if result["confidence"] >= 0.6:
            result["verified"] = True
            result["reason"] += " (ATS platform detected with form elements)"

    return result


async def verify_and_update_job(job) -> dict:
    """Full verification pipeline for a single job.

    1. Verify existing URL
    2. If fails, use Gemini to find a better URL
    3. Verify the new URL
    4. Update job fields
    """
    from store import store

    # Try verifying the existing URL first
    existing_url = job.job_url or job.company_website or ""
    result = await verify_application_link(
        existing_url, job.role_title, job.company_name,
        f"{job.city or ''} {job.country or ''}".strip()
    )

    if result["verified"]:
        job.verified_url = result["apply_url"]
        job.url_verified = True
        job.url_verification_error = None
        store.update_job(job)
        logger.info(f"[link_verifier] Verified: {job.company_name} / {job.role_title} -> {result['apply_url']}")
        return result

    # If existing URL failed, try to discover a better one
    discovered_url = await find_direct_apply_url(
        job.company_name, job.role_title,
        job.company_website, existing_url
    )

    if discovered_url and discovered_url != existing_url:
        result2 = await verify_application_link(
            discovered_url, job.role_title, job.company_name,
            f"{job.city or ''} {job.country or ''}".strip()
        )
        if result2["verified"]:
            job.verified_url = result2["apply_url"]
            job.url_verified = True
            job.url_verification_error = None
            store.update_job(job)
            logger.info(f"[link_verifier] Discovered & verified: {job.company_name} -> {result2['apply_url']}")
            return result2
        result = result2  # Use the latest attempt's info

    # Mark as verified but failed
    job.url_verified = True  # Mark as checked (even if failed)
    job.url_verification_error = result.get("reason", "Verification failed")
    store.update_job(job)
    logger.info(f"[link_verifier] Failed: {job.company_name} / {job.role_title}: {result.get('reason')}")
    return result


async def run_background_verification(batch_size: int = 50, delay: float = 2.0):
    """Background task: verify unverified job URLs at a steady rate."""
    from store import store

    logger.info("[link_verifier] Starting background URL verification...")
    jobs = store.get_unverified_jobs(limit=batch_size)
    logger.info(f"[link_verifier] Found {len(jobs)} unverified jobs")

    verified_count = 0
    failed_count = 0

    for job in jobs:
        try:
            result = await verify_and_update_job(job)
            if result.get("verified"):
                verified_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"[link_verifier] Error verifying {job.company_name}: {e}")
            failed_count += 1

        # Rate limit
        await asyncio.sleep(delay)

    logger.info(
        f"[link_verifier] Verification complete: "
        f"{verified_count} verified, {failed_count} failed, out of {len(jobs)} total"
    )
