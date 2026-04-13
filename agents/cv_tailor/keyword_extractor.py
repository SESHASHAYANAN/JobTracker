"""Keyword extraction from job descriptions using Groq.

Fast extraction (~0.3s) of ATS-critical keywords and competency grid building.
"""
from __future__ import annotations

from agents.llm.groq_client import GroqClient


async def extract_keywords(
    jd_text: str, groq: GroqClient, count: int = 20
) -> list[str]:
    """Extract ATS-critical keywords from a job description.

    Returns keywords ordered by importance (most critical first).
    Includes technical skills, tools, methodologies, and domain terms.
    """
    try:
        keywords = await groq.extract_keywords(jd_text, count=count)
        if keywords:
            return keywords
    except Exception as e:
        print(f"    [keywords] LLM extraction failed: {e}")

    # Fallback: simple keyword extraction
    return _fallback_extract(jd_text, count)


async def build_competency_grid(
    keywords: list[str], jd_text: str, groq: GroqClient, count: int = 8
) -> list[str]:
    """Select 6-8 keyword phrases for the Core Competencies section.

    These are short, impactful phrases from the JD requirements —
    not raw keywords but "competency-level" phrases suitable for
    a CV grid/sidebar.
    """
    try:
        result = await groq.extract_json(
            f"From these ATS keywords and the job description, create {count} "
            f"short competency phrases (2-4 words each) suitable for a CV "
            f"'Core Competencies' grid section.\n\n"
            f"Keywords: {', '.join(keywords[:15])}\n\n"
            f"JD excerpt: {jd_text[:1500]}\n\n"
            f"Return a JSON array of {count} strings."
        )
        if isinstance(result, list):
            return result[:count]
        if isinstance(result, dict) and "competencies" in result:
            return result["competencies"][:count]
    except Exception as e:
        print(f"    [competencies] LLM failed: {e}")

    # Fallback: use top keywords as-is
    return keywords[:count]


def _fallback_extract(jd_text: str, count: int) -> list[str]:
    """Simple keyword extraction without LLM."""
    # Common tech/role keywords
    tech_keywords = {
        "python", "javascript", "typescript", "java", "go", "rust", "c++",
        "react", "node.js", "aws", "gcp", "azure", "kubernetes", "docker",
        "sql", "nosql", "postgresql", "mongodb", "redis", "elasticsearch",
        "machine learning", "deep learning", "nlp", "llm", "rag",
        "api", "rest", "graphql", "microservices", "ci/cd", "devops",
        "agile", "scrum", "product management", "data engineering",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "spark",
    }

    jd_lower = jd_text.lower()
    found = [kw for kw in tech_keywords if kw in jd_lower]
    return sorted(found, key=lambda k: jd_lower.count(k), reverse=True)[:count]
