"""CV section rewriting using Gemini for long-context tailoring.

Each function rewrites a specific CV section while preserving factual accuracy.
"""
from __future__ import annotations

from agents.llm.gemini_client import GeminiClient


async def rewrite_summary(
    original: str,
    keywords: list[str],
    archetype: str,
    jd_text: str,
    gemini: GeminiClient,
) -> str:
    """Rewrite the Professional Summary to inject top JD keywords.

    Rules (from career-ops pdf.md):
    - 3-4 lines, keyword-dense
    - NEVER invent experience
    - Inject keywords naturally into existing text
    - Adapt framing for the role archetype
    """
    return await gemini.rewrite_section(
        section_name="Professional Summary",
        original_text=original,
        keywords=keywords[:7],
        jd_context=jd_text[:2000],
        archetype=archetype,
    )


async def reorder_experience(
    original: str,
    jd_text: str,
    keywords: list[str],
    gemini: GeminiClient,
) -> str:
    """Reorder experience bullets by JD relevance.

    Most relevant bullets move to the top of each role section.
    Keywords are injected naturally into existing achievements.
    """
    prompt = (
        "You are an expert ATS-optimized resume writer.\n\n"
        "Rewrite and reorder this Work Experience section so the most relevant "
        "achievements for the target job appear first in each role.\n\n"
        f"Target keywords to emphasize: {', '.join(keywords[:10])}\n\n"
        f"--- ORIGINAL EXPERIENCE ---\n{original}\n\n"
        f"--- TARGET JOB DESCRIPTION ---\n{jd_text[:2000]}\n\n"
        "RULES:\n"
        "- Keep ALL roles and dates unchanged\n"
        "- Reorder bullets within each role by relevance to the target JD\n"
        "- Reformulate bullets to use JD vocabulary where truthful\n"
        "- NEVER add achievements or skills the candidate doesn't have\n"
        "- Use action verbs, quantify results where possible\n"
        "- First bullet of each role should be most relevant to the JD\n\n"
        "Return ONLY the rewritten experience section, no explanations."
    )
    return await gemini.analyze(prompt, max_tokens=3000)


async def select_projects(
    original: str,
    jd_text: str,
    keywords: list[str],
    gemini: GeminiClient,
) -> str:
    """Select and reframe the top 3-4 most relevant projects.

    Projects are selected based on alignment with JD requirements.
    """
    prompt = (
        "You are an expert ATS-optimized resume writer.\n\n"
        "Select the 3-4 most relevant projects from this section for the target job. "
        "Reframe their descriptions to emphasize alignment with the JD.\n\n"
        f"Target keywords: {', '.join(keywords[:10])}\n\n"
        f"--- ALL PROJECTS ---\n{original}\n\n"
        f"--- TARGET JOB DESCRIPTION ---\n{jd_text[:1500]}\n\n"
        "RULES:\n"
        "- Select ONLY 3-4 most relevant projects\n"
        "- Reframe descriptions using JD vocabulary\n"
        "- NEVER invent project details\n"
        "- Highlight metrics and outcomes\n\n"
        "Return ONLY the selected projects section, no explanations."
    )
    return await gemini.analyze(prompt, max_tokens=2000)


async def inject_keywords(
    section_text: str,
    keywords: list[str],
    jd_text: str,
    gemini: GeminiClient,
) -> str:
    """Inject JD keywords naturally into existing text.

    Reformulation examples (from career-ops pdf.md):
    - 'LLM workflows with retrieval' → 'RAG pipeline design and LLM orchestration workflows'
    - 'observability, evals, error handling' → 'MLOps and observability: evals, error handling'
    - 'collaborated with team' → 'stakeholder management across engineering and ops'

    NEVER adds skills the candidate doesn't have.
    """
    prompt = (
        "You are an expert ATS resume optimizer.\n\n"
        "Inject these keywords naturally into the existing text. "
        "ONLY reformulate — NEVER add new skills or experience.\n\n"
        f"Keywords to inject: {', '.join(keywords[:12])}\n\n"
        f"--- ORIGINAL TEXT ---\n{section_text}\n\n"
        f"--- JD CONTEXT ---\n{jd_text[:1000]}\n\n"
        "Return ONLY the updated text with keywords injected naturally."
    )
    return await gemini.analyze(prompt, max_tokens=2000)
