"""Startup Classifier — heuristics-based startup/stealth detection and ranking."""
from __future__ import annotations
from models import Job


# ── Signals ──────────────────────────────────────────────────────

STARTUP_ROLE_KEYWORDS = {
    "founding engineer", "founding", "early team", "employee #",
    "0 to 1", "zero to one", "build from scratch", "greenfield",
    "first engineer", "first hire",
}

STARTUP_JD_KEYWORDS = {
    "seed", "series a", "series b", "pre-seed",
    "early stage", "early-stage", "startup", "start-up",
    "fast-paced", "high-growth", "fast growing",
    "equity", "esops", "stock options", "founding",
    "venture", "vc-backed", "backed by", "funded by",
    "small team", "lean team", "scrappy",
}

ENGINEERING_KEYWORDS = {
    "software engineer", "backend engineer", "frontend engineer",
    "full stack", "fullstack", "devops", "sre", "platform engineer",
    "ml engineer", "machine learning engineer", "ai engineer",
    "data engineer", "mobile engineer", "product engineer",
    "founding engineer", "staff engineer", "principal engineer",
    "qa engineer", "sdet", "site reliability",
}

STEALTH_SIGNALS = {
    "stealth", "stealth mode", "stealth startup",
    "confidential", "undisclosed", "pre-launch",
}

INDIA_CITIES = {
    "bengaluru", "bangalore", "mumbai", "delhi", "delhi ncr",
    "new delhi", "gurgaon", "gurugram", "noida", "hyderabad",
    "chennai", "pune", "kolkata", "ahmedabad", "jaipur",
    "kochi", "thiruvananthapuram", "coimbatore", "indore",
    "chandigarh", "lucknow", "remote india", "india",
}


# ── Classification Functions ─────────────────────────────────────

def classify_startup(job: Job) -> tuple[bool, float, list[str]]:
    """Classify a job as startup based on heuristics.

    Returns (is_startup, confidence, tags).
    """
    if job.is_startup and job.startup_confidence > 0:
        return (job.is_startup, job.startup_confidence, job.startup_tags)

    score = 0.0
    tags: list[str] = []

    # Team size signal
    ts = job.team_size or 0
    if 0 < ts <= 10:
        score += 0.25
        tags.append("Micro Team")
    elif 10 < ts <= 50:
        score += 0.20
        tags.append("Early Team")
    elif 50 < ts <= 200:
        score += 0.10
        tags.append("Growth Startup")
    elif 200 < ts <= 500:
        score += 0.05

    # Stage signal
    stage = (job.stage or "").lower()
    stage_map = {
        "pre-seed": (0.25, "Pre-Seed"),
        "seed": (0.22, "Seed"),
        "early": (0.15, "Early Stage"),
        "series a": (0.18, "Series A"),
        "series b": (0.12, "Series B"),
        "series c": (0.08, "Series C"),
        "growth": (0.05, "Growth"),
    }
    for key, (boost, tag) in stage_map.items():
        if key in stage:
            score += boost
            tags.append(tag)
            break

    # VC backers signal
    if job.vc_backers:
        elite_vcs = {"y combinator", "a16z", "sequoia", "lightspeed", "peak xv",
                     "accel", "nexus", "matrix partners", "tiger global", "kalaari",
                     "blume ventures", "chiratae", "3one4", "elevation capital"}
        for vc in job.vc_backers:
            if vc.lower() in elite_vcs:
                score += 0.10
                tags.append(f"VC: {vc}")
                break

    # Role title signals
    title_lower = (job.role_title or "").lower()
    for kw in STARTUP_ROLE_KEYWORDS:
        if kw in title_lower:
            score += 0.15
            tags.append("Founding Role")
            break

    # JD keyword signals
    jd_lower = (job.job_description or "").lower()
    startup_kw_count = sum(1 for kw in STARTUP_JD_KEYWORDS if kw in jd_lower)
    if startup_kw_count >= 3:
        score += 0.15
    elif startup_kw_count >= 1:
        score += 0.08

    # Source signal
    startup_sources = {"yc_oss_api", "yc_generative_ai", "yc_workatastartup",
                       "wellfound", "startup_directories", "startup_seed",
                       "hn_hiring", "funding_news", "diverse_seed"}
    if job.source in startup_sources:
        score += 0.10
        tags.append("Startup Source")

    # Company name signals (stealth etc)
    name_lower = (job.company_name or "").lower()
    if any(s in name_lower for s in STEALTH_SIGNALS):
        score += 0.10
        tags.append("Stealth")

    confidence = min(score, 1.0)
    is_startup = confidence >= 0.25
    tags.append("Startup") if is_startup else None

    return (is_startup, round(confidence, 2), [t for t in tags if t])


def detect_stealth(job: Job) -> bool:
    """Detect if job is from a stealth startup."""
    if job.is_stealth:
        return True
    name_lower = (job.company_name or "").lower()
    jd_lower = (job.job_description or "").lower()
    combined = name_lower + " " + jd_lower
    return any(s in combined for s in STEALTH_SIGNALS)


def is_engineering_role(job: Job) -> bool:
    """Check if job is an engineering role."""
    title_lower = (job.role_title or "").lower()
    category_lower = (job.role_category or "").lower()
    return (
        any(kw in title_lower for kw in ENGINEERING_KEYWORDS)
        or category_lower in ("engineering", "backend", "frontend", "devops",
                              "ai/ml", "data", "mobile", "qa / testing")
    )


def is_india_based(job: Job) -> bool:
    """Check if job is India-based or remote-India."""
    country = (job.country or "").lower()
    city = (job.city or "").lower()
    work = (job.work_type or "").lower()
    tags_lower = " ".join(job.startup_tags + job.industry_tags).lower()

    if country in ("india",):
        return True
    if city in INDIA_CITIES:
        return True
    if "india" in tags_lower or "remote india" in tags_lower:
        return True
    return False


def compute_startup_rank(job: Job) -> float:
    """Compute startup-first ranking score."""
    score = job.relevance_score or 0.3

    # Startup boost
    if job.is_startup:
        score += 0.15
    if job.is_stealth:
        score += 0.05

    # India boost
    if is_india_based(job):
        score += 0.10

    # Engineering boost
    if is_engineering_role(job):
        score += 0.10

    # Founding role boost
    title_lower = (job.role_title or "").lower()
    if "founding" in title_lower:
        score += 0.10

    # Freshness boost
    if job.posted_date:
        try:
            from datetime import datetime
            posted = datetime.fromisoformat(job.posted_date)
            age_days = (datetime.utcnow() - posted).days
            if age_days <= 3:
                score += 0.10
            elif age_days <= 7:
                score += 0.07
            elif age_days <= 14:
                score += 0.03
        except Exception:
            pass

    # Match score boost
    if job.match_score and job.match_score > 60:
        score += 0.10

    # Startup confidence pro-rate
    score += job.startup_confidence * 0.1

    return min(round(score, 2), 1.0)


def classify_and_enrich(job: Job) -> Job:
    """Run full classification pipeline on a job."""
    is_startup, confidence, tags = classify_startup(job)
    job.is_startup = is_startup
    job.startup_confidence = confidence
    job.is_stealth = detect_stealth(job)

    # Merge tags without duplicates
    existing = set(job.startup_tags)
    for t in tags:
        if t not in existing:
            job.startup_tags.append(t)
            existing.add(t)

    # Infer stage from team size if missing
    if not job.startup_stage and is_startup:
        ts = job.team_size or 0
        if ts <= 10:
            job.startup_stage = "Pre-Seed"
        elif ts <= 50:
            job.startup_stage = "Seed"
        elif ts <= 200:
            job.startup_stage = "Series A"
        elif ts <= 500:
            job.startup_stage = "Series B"
        else:
            job.startup_stage = "Growth"

    return job
