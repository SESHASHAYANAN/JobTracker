"""Resume Matcher — AI-powered job matching using Groq/Gemini.

Replaces keyword heuristics with real LLM inference:
- Phase 1 (Groq): Fast batch scoring of jobs against resume
- Phase 2 (Gemini): Deep comparison for top candidates
"""
from __future__ import annotations
import json
import os
import logging
from typing import Optional

from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

from models import Job
from services.resume_parser import extract_skills, extract_experience_level, extract_role_preferences

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(_project_root, '.env'))

logger = logging.getLogger(__name__)

_groq = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
_gemini_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_key:
    genai.configure(api_key=_gemini_key)
_gemini = genai.GenerativeModel("gemini-2.0-flash")


async def _groq_batch_score(resume_summary: str, jobs_batch: list[dict]) -> list[dict]:
    """Use Groq for fast batch scoring of jobs against resume.

    Returns list of {job_id, score, reasons} for each job in the batch.
    """
    jobs_text = ""
    for i, j in enumerate(jobs_batch):
        jobs_text += (
            f"\n[JOB {i+1}] id={j['id']}\n"
            f"Title: {j['role_title']} at {j['company_name']}\n"
            f"Category: {j.get('role_category', 'N/A')}\n"
            f"Level: {j.get('experience_level', 'N/A')}\n"
            f"Tags: {', '.join(j.get('industry_tags', [])[:5])}\n"
            f"JD: {(j.get('jd_summary') or j.get('job_description') or '')[:300]}\n"
        )

    try:
        resp = _groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert job-resume matcher. Score each job's fit "
                        "with the candidate on a 0-100 scale. Respond with ONLY valid JSON: "
                        "an array of objects with keys: job_id (string), score (int 0-100), "
                        "reasons (array of 2-3 short reason strings). "
                        "No markdown fences. Be strict — only score high if there's genuine alignment."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"--- CANDIDATE PROFILE ---\n{resume_summary[:2000]}\n\n"
                        f"--- JOBS TO EVALUATE ---\n{jobs_text}\n\n"
                        "Score each job."
                    ),
                },
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"[resume_matcher] Groq batch score error: {e}")
        return []


async def _gemini_deep_compare(resume_text: str, jd_text: str, role_title: str, company_name: str) -> dict:
    """Use Gemini for deep comparison of resume vs single JD.

    Returns {score, matched_skills, gaps, reasons, strengths}.
    """
    try:
        prompt = (
            "You are an expert career evaluator. Compare this candidate's resume "
            "against the job description and provide a detailed fit assessment.\n\n"
            f"--- RESUME ---\n{resume_text[:3000]}\n\n"
            f"--- JOB: {role_title} at {company_name} ---\n{jd_text[:2000]}\n\n"
            "Return ONLY valid JSON with keys:\n"
            "score (int 0-100), matched_skills (array of strings), "
            "gaps (array of strings), reasons (array of 3-5 match reason strings), "
            "strengths (array of candidate advantages). No markdown fences."
        )
        resp = _gemini.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=1500,
                temperature=0.2,
            ),
        )
        raw = resp.text.strip() if resp.text else "{}"
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[resume_matcher] Gemini deep compare error: {e}")
        return {}


def _keyword_fallback_score(resume_text: str, job: Job) -> tuple[float, list[str], list[str]]:
    """Fallback keyword-based scoring when LLMs are unavailable."""
    skills = extract_skills(resume_text)
    level = extract_experience_level(resume_text)
    role_prefs = extract_role_preferences(resume_text)
    resume_lower = resume_text.lower()

    score = 0.0
    reasons = []
    matched_skills = []

    job_blob = f"{job.role_title} {job.job_description or ''} {job.jd_summary or ''} {' '.join(job.industry_tags)}".lower()
    for skill in skills:
        if skill in job_blob:
            matched_skills.append(skill)
    skill_score = min(len(matched_skills) * 5, 40)
    score += skill_score
    if matched_skills:
        reasons.append(f"Skills: {', '.join(matched_skills[:5])}")

    if job.role_category:
        for pref in role_prefs:
            if pref.lower() in job.role_category.lower():
                score += 30
                reasons.append(f"Role match: {pref}")
                break

    if job.experience_level and level:
        if job.experience_level.lower() == level.lower():
            score += 15
            reasons.append(f"Level match: {level}")

    score += job.relevance_score * 5

    return score, matched_skills, reasons


async def match_jobs_to_resume(
    resume_text: str,
    jobs: list[Job],
    top_k: int = 20,
) -> list[dict]:
    """Score each job against the resume using AI and return top matches.

    Pipeline:
    1. Filter to active/hiring jobs
    2. Groq batch scoring (fast, ~0.5s per batch of 5)
    3. Gemini deep analysis for top 10 (detailed reasoning)
    4. Merge scores and return ranked results
    """
    # Filter active jobs
    active_jobs = [j for j in jobs if j.is_hiring and j.status == "active"]
    if not active_jobs:
        return []

    # Build resume summary for Groq
    resume_summary = resume_text[:3000]

    # Phase 1: Groq batch scoring
    all_scores: dict[str, dict] = {}
    batch_size = 5
    job_dicts = [j.model_dump() for j in active_jobs]

    for i in range(0, len(job_dicts), batch_size):
        batch = job_dicts[i:i + batch_size]
        try:
            batch_results = await _groq_batch_score(resume_summary, batch)
            for item in batch_results:
                jid = item.get("job_id", "")
                if jid:
                    all_scores[jid] = {
                        "score": item.get("score", 0),
                        "reasons": item.get("reasons", []),
                        "matched_skills": [],
                    }
        except Exception as e:
            logger.warning(f"[resume_matcher] Batch {i} failed, using fallback: {e}")
            # Fallback for this batch
            for jd in batch:
                job_obj = next((j for j in active_jobs if j.id == jd["id"]), None)
                if job_obj:
                    score, skills, reasons = _keyword_fallback_score(resume_text, job_obj)
                    all_scores[jd["id"]] = {
                        "score": round(score, 1),
                        "reasons": reasons,
                        "matched_skills": skills,
                    }

    # For jobs that weren't scored (API failures), use keyword fallback
    for job in active_jobs:
        if job.id not in all_scores:
            score, skills, reasons = _keyword_fallback_score(resume_text, job)
            all_scores[job.id] = {
                "score": round(score, 1),
                "reasons": reasons,
                "matched_skills": skills,
            }

    # Sort by score and take top candidates
    sorted_ids = sorted(all_scores.keys(), key=lambda k: all_scores[k]["score"], reverse=True)
    top_ids = sorted_ids[:top_k]

    # Phase 2: Gemini deep analysis for top 10
    for job_id in top_ids[:10]:
        job = next((j for j in active_jobs if j.id == job_id), None)
        if not job:
            continue
        jd_text = job.jd_summary or job.job_description or ""
        if not jd_text:
            continue
        try:
            deep = await _gemini_deep_compare(
                resume_text, jd_text, job.role_title, job.company_name
            )
            if deep:
                # Merge Gemini's deeper analysis with Groq's score
                groq_score = all_scores[job_id]["score"]
                gemini_score = deep.get("score", groq_score)
                # Weighted average: 40% Groq (fast), 60% Gemini (deep)
                merged_score = round(groq_score * 0.4 + gemini_score * 0.6, 1)
                all_scores[job_id]["score"] = merged_score
                all_scores[job_id]["reasons"] = deep.get("reasons", all_scores[job_id]["reasons"])
                all_scores[job_id]["matched_skills"] = deep.get("matched_skills", [])
        except Exception as e:
            logger.warning(f"[resume_matcher] Gemini deep compare failed for {job_id}: {e}")

    # Re-sort after Gemini refinement
    top_ids = sorted(top_ids, key=lambda k: all_scores.get(k, {}).get("score", 0), reverse=True)

    # Build final results
    results = []
    for job_id in top_ids:
        job = next((j for j in active_jobs if j.id == job_id), None)
        if not job:
            continue
        meta = all_scores.get(job_id, {})
        results.append({
            "job": job.model_dump(),
            "match_score": meta.get("score", 0),
            "matched_skills": meta.get("matched_skills", [])[:8],
            "reasons": meta.get("reasons", [])[:5],
        })

    return results
