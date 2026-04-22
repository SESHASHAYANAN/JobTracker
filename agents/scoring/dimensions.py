"""10 scoring dimensions for job evaluation.

Adapted from career-ops modes/_shared.md scoring system.
Each dimension has a name, weight, and description used as the scoring prompt.
"""
from __future__ import annotations

# Dimension definitions — weights must sum to 1.0
DIMENSIONS: list[dict] = [
    {
        "name": "cv_match",
        "weight": 0.20,
        "description": (
            "Skills, experience, and proof points alignment with JD requirements. "
            "Score 5 if the candidate's CV directly addresses 90%+ of listed requirements. "
            "Score 1 if fewer than 20% of requirements are covered."
        ),
    },
    {
        "name": "north_star_alignment",
        "weight": 0.15,
        "description": (
            "How well the role fits the candidate's target career direction and goals. "
            "Score 5 if the role perfectly aligns with their stated career objectives. "
            "Score 1 if it's a significant detour from their trajectory."
        ),
    },
    {
        "name": "compensation",
        "weight": 0.12,
        "description": (
            "Salary and total compensation vs market rate for this role and seniority. "
            "Score 5 if top quartile compensation. "
            "Score 1 if significantly below market (>30% under)."
        ),
    },
    {
        "name": "growth_potential",
        "weight": 0.10,
        "description": (
            "Learning opportunities, career trajectory, mentorship, and skill development. "
            "Score 5 if the role offers significant growth in new technologies or leadership. "
            "Score 1 if it's a lateral move with no upside."
        ),
    },
    {
        "name": "technical_depth",
        "weight": 0.10,
        "description": (
            "Technical complexity and challenge level of the role. "
            "Score 5 if the role involves cutting-edge work pushing technical boundaries. "
            "Score 1 if the work is rote or purely operational."
        ),
    },
    {
        "name": "culture_signals",
        "weight": 0.08,
        "description": (
            "Company culture, values alignment, team dynamics, and work environment signals. "
            "Score 5 if strong positive culture signals (engineering-driven, transparent, diverse). "
            "Score 1 if red flags (high turnover, toxic Glassdoor reviews, unrealistic expectations)."
        ),
    },
    {
        "name": "company_stability",
        "weight": 0.08,
        "description": (
            "Funding, revenue trajectory, market position, runway, and business viability. "
            "Score 5 if well-funded with strong market position or profitable. "
            "Score 1 if early-stage with uncertain runway or negative signals."
        ),
    },
    {
        "name": "brand_value",
        "weight": 0.07,
        "description": (
            "Resume value — how much this role enhances the candidate's professional brand. "
            "Score 5 if a top-tier company recognized industry-wide. "
            "Score 1 if no brand recognition or negative brand associations."
        ),
    },
    {
        "name": "remote_flexibility",
        "weight": 0.05,
        "description": (
            "Remote policy, timezone flexibility, async culture, and work-life balance. "
            "Score 5 if fully remote with async-first culture. "
            "Score 1 if strict on-site with rigid hours."
        ),
    },
    {
        "name": "red_flags",
        "weight": 0.05,
        "description": (
            "Negative signals that could be deal-breakers. This dimension is INVERTED — "
            "Score 5 if NO red flags detected (best case). "
            "Score 1 if critical red flags found (unrealistic requirements, poor reviews, "
            "deceptive JD language, extremely broad role scope suggesting understaffing)."
        ),
    },
]


def get_dimension_names() -> list[str]:
    """Return all dimension names."""
    return [d["name"] for d in DIMENSIONS]


def get_grade_label(score: float) -> str:
    """Map a numeric score (1-5) to a letter grade with label."""
    if score >= 4.5:
        return "A — Strong match, apply immediately"
    elif score >= 4.0:
        return "B — Good match, worth applying"
    elif score >= 3.5:
        return "C — Decent, apply only with specific reason"
    elif score >= 3.0:
        return "D — Marginal, recommend against"
    elif score >= 2.5:
        return "E — Poor fit"
    else:
        return "F — No match, skip"
