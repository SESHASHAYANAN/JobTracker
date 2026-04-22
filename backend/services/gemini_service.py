"""Gemini AI service — JD summarisation, field inference."""
from __future__ import annotations
import os, json
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(_project_root, '.env'))
_gemini_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_key:
    genai.configure(api_key=_gemini_key)

_model = genai.GenerativeModel("gemini-2.0-flash")


async def summarise_jd(job_description: str) -> str:
    if not job_description or len(job_description) < 30:
        return job_description or ""
    try:
        prompt = (
            "Summarise this job description in exactly 3 concise lines. "
            "Focus on: role responsibilities, key requirements, and what makes "
            "this role unique. No bullet points.\n\n"
            f"{job_description[:3000]}"
        )
        resp = _model.generate_content(prompt)
        return resp.text.strip() if resp.text else ""
    except Exception as e:
        print(f"[gemini] summarise error: {e}")
        return ""


async def infer_job_fields(job_description: str, role_title: str = "") -> dict:
    """Use Gemini to infer visa, level, salary, tags from JD text."""
    if not job_description:
        return {}
    try:
        prompt = (
            "Given this job posting, extract the following fields as JSON:\n"
            '{"visa_sponsorship": "Yes/No/Unknown", '
            '"experience_level": "New Grad/Mid/Senior", '
            '"salary_range": "string or null", '
            '"work_type": "onsite/remote/hybrid/Unknown", '
            '"role_category": "one of: AI/ML, Engineering, Design, GTM, Data, Ops, Other", '
            '"industry_tags": ["tag1","tag2"]}\n\n'
            f"Role title: {role_title}\n"
            f"Job description:\n{job_description[:3000]}"
        )
        resp = _model.generate_content(prompt)
        text = resp.text.strip() if resp.text else "{}"
        # strip markdown fences
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception as e:
        print(f"[gemini] infer error: {e}")
        return {}


async def parse_funding_news(text: str) -> list[dict]:
    """Parse funding news text into structured records."""
    try:
        prompt = (
            "Extract startup funding announcements from this text. "
            "Return a JSON array of objects with fields: "
            "company, round, amount, lead_vc, website (if found).\n\n"
            f"{text[:4000]}"
        )
        resp = _model.generate_content(prompt)
        raw = resp.text.strip() if resp.text else "[]"
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return []


async def parse_hn_post(post_text: str) -> Optional[dict]:
    """Parse a single HN 'Who is Hiring' post into job fields."""
    try:
        prompt = (
            "Parse this Hacker News hiring post into JSON with fields: "
            "company_name, role_title, location, salary_range, work_type, "
            "job_url, visa_sponsorship, email. Return null for missing fields.\n\n"
            f"{post_text[:2000]}"
        )
        resp = _model.generate_content(prompt)
        raw = resp.text.strip() if resp.text else "{}"
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return None
