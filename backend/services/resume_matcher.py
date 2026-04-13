"""Resume Matcher — scores and ranks jobs against resume content."""
from __future__ import annotations
from models import Job
from services.resume_parser import extract_skills, extract_experience_level, extract_role_preferences


def match_jobs_to_resume(
    resume_text: str,
    jobs: list[Job],
    top_k: int = 20,
) -> list[dict]:
    """Score each job against the resume and return top matches."""
    skills = extract_skills(resume_text)
    level = extract_experience_level(resume_text)
    role_prefs = extract_role_preferences(resume_text)
    resume_lower = resume_text.lower()

    scored: list[tuple[float, Job, dict]] = []

    for job in jobs:
        if not job.is_hiring or job.status != "active":
            continue

        score = 0.0
        reasons: list[str] = []

        # ── Role category match (0-30 pts) ────────────────
        if job.role_category:
            for pref in role_prefs:
                if pref.lower() in job.role_category.lower():
                    score += 30
                    reasons.append(f"Role match: {pref}")
                    break

        # ── Skill keyword match (0-40 pts) ────────────────
        skill_hits = 0
        job_blob = f"{job.role_title} {job.job_description or ''} {job.jd_summary or ''} {' '.join(job.industry_tags)}".lower()
        matched_skills = []
        for skill in skills:
            if skill in job_blob:
                skill_hits += 1
                matched_skills.append(skill)
        skill_score = min(skill_hits * 5, 40)
        score += skill_score
        if matched_skills:
            reasons.append(f"Skills: {', '.join(matched_skills[:5])}")

        # ── Experience level match (0-15 pts) ─────────────
        if job.experience_level and level:
            if job.experience_level.lower() == level.lower():
                score += 15
                reasons.append(f"Level match: {level}")
            elif (level == "Senior" and job.experience_level.lower() == "mid") or \
                 (level == "Mid" and job.experience_level.lower() in ("new grad", "senior")):
                score += 5

        # ── Industry tag match (0-10 pts) ────────────────
        for tag in job.industry_tags:
            if tag.lower() in resume_lower:
                score += 3
                reasons.append(f"Industry: {tag}")
                if score >= 10:
                    break

        # ── Company name / technology mention (0-5 pts) ──
        if job.company_name.lower() in resume_lower:
            score += 5
            reasons.append(f"Company mentioned: {job.company_name}")

        # ── Base relevance boost ─────────────────────────
        score += job.relevance_score * 5

        scored.append((score, job, {
            "score": round(score, 1),
            "matched_skills": matched_skills[:8],
            "experience_level": level,
            "role_preferences": role_prefs,
            "reasons": reasons[:5],
        }))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score_val, job, meta in scored[:top_k]:
        results.append({
            "job": job.model_dump(),
            "match_score": meta["score"],
            "matched_skills": meta["matched_skills"],
            "reasons": meta["reasons"],
        })

    return results
