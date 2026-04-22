"""Resume Rewriter — ATS-optimized resume rewriting using Gemini/Groq.

When Advanced mode is on:
1. Fetches GitHub profile data (public API, no key needed)
2. Reads LinkedIn summary from user profile data
3. Uses Gemini (long context) to rewrite resume sections for ATS optimization
4. Returns structured diffs for the Canva-style editor
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Optional, AsyncGenerator

import httpx
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(_project_root, '.env'))

logger = logging.getLogger(__name__)

_groq = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
_gemini_key = os.getenv("GEMINI_API_KEY", "")
if _gemini_key:
    genai.configure(api_key=_gemini_key)
_gemini = genai.GenerativeModel("gemini-2.0-flash")


async def fetch_github_profile(github_url: str) -> dict:
    """Fetch public GitHub profile data.

    Returns dict with:
      - name, bio, public_repos, followers
      - top_repos: [{name, description, language, stars, url}]
      - languages: [str]
    """
    if not github_url:
        return {}

    # Extract username from URL
    username = github_url.rstrip("/").split("/")[-1]
    if not username:
        return {}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch user profile
            resp = await client.get(f"https://api.github.com/users/{username}")
            if resp.status_code != 200:
                logger.warning(f"[resume_rewriter] GitHub API returned {resp.status_code} for {username}")
                return {}
            user_data = resp.json()

            # Fetch repos (sorted by stars)
            repos_resp = await client.get(
                f"https://api.github.com/users/{username}/repos",
                params={"sort": "stars", "direction": "desc", "per_page": 10},
            )
            repos = repos_resp.json() if repos_resp.status_code == 200 else []

            # Extract languages from repos
            languages = set()
            top_repos = []
            for repo in repos[:10]:
                if repo.get("fork"):
                    continue
                if repo.get("language"):
                    languages.add(repo["language"])
                top_repos.append({
                    "name": repo.get("name", ""),
                    "description": repo.get("description", ""),
                    "language": repo.get("language", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "url": repo.get("html_url", ""),
                })

            return {
                "name": user_data.get("name", ""),
                "bio": user_data.get("bio", ""),
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "top_repos": top_repos[:6],
                "languages": list(languages),
                "profile_url": github_url,
            }
    except Exception as e:
        logger.error(f"[resume_rewriter] GitHub fetch error: {e}")
        return {}


async def extract_ats_keywords(jd_text: str) -> list[str]:
    """Use Groq (fast) to extract ATS-critical keywords from a JD."""
    try:
        resp = _groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract ATS-critical keywords from this job description. "
                        "Return ONLY a JSON array of strings, ordered by importance. "
                        "Include technical skills, tools, methodologies, and domain terms. "
                        "Extract 15-25 keywords."
                    ),
                },
                {"role": "user", "content": jd_text[:3000]},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"[resume_rewriter] ATS keyword extraction error: {e}")
        return []


async def rewrite_resume_for_jd(
    resume_text: str,
    jd_text: str,
    job_title: str = "",
    company_name: str = "",
    github_data: Optional[dict] = None,
    linkedin_url: Optional[str] = None,
) -> dict:
    """Rewrite resume to be ATS-optimized for a specific JD.

    Uses Gemini (long context window) for deep section-by-section rewriting.

    Returns:
    {
        sections: [{name, original, rewritten, changes: [{type, before, after}]}],
        ats_score_before: int (0-100),
        ats_score_after: int (0-100),
        keywords_added: [str],
        summary: str
    }
    """
    # Build enhancement context from GitHub
    github_context = ""
    if github_data:
        repos_str = ""
        for repo in github_data.get("top_repos", [])[:4]:
            repos_str += (
                f"- {repo['name']}: {repo['description'] or 'No description'} "
                f"({repo['language']}, {repo['stars']} stars)\n"
            )
        github_context = (
            f"\n--- GITHUB PROFILE ---\n"
            f"Name: {github_data.get('name', 'N/A')}\n"
            f"Bio: {github_data.get('bio', 'N/A')}\n"
            f"Public repos: {github_data.get('public_repos', 0)}\n"
            f"Followers: {github_data.get('followers', 0)}\n"
            f"Languages: {', '.join(github_data.get('languages', []))}\n"
            f"Top repos:\n{repos_str}"
        )

    linkedin_context = ""
    if linkedin_url:
        linkedin_context = f"\n--- LINKEDIN ---\nProfile: {linkedin_url}\n"

    try:
        prompt = (
            "You are an expert ATS-optimized resume writer. Rewrite this resume to maximize "
            "match score for the target job description.\n\n"
            f"Target Role: {job_title} at {company_name}\n\n"
            "--- ORIGINAL RESUME ---\n"
            f"{resume_text}\n\n"
            "--- JOB DESCRIPTION ---\n"
            f"{jd_text[:4000]}\n"
            f"{github_context}"
            f"{linkedin_context}\n"
            "CRITICAL RULES:\n"
            "- NEVER invent skills or experience the candidate doesn't have\n"
            "- ONLY reformulate existing text using JD vocabulary\n"
            "- Inject ATS keywords naturally into existing achievements\n"
            "- If GitHub data is provided, add a 'Projects' section with relevant repos\n"
            "- Use action verbs, quantify accomplishments where data exists\n"
            "- Avoid clichés: 'passionate about', 'proven track record'\n\n"
            "Return ONLY valid JSON with this structure:\n"
            "{\n"
            '  "sections": [\n'
            '    {"name": "Summary", "original": "...", "rewritten": "...", '
            '"changes": [{"type": "modify", "before": "old text", "after": "new text"}]},\n'
            '    {"name": "Experience", "original": "...", "rewritten": "...", "changes": [...]},\n'
            '    {"name": "Skills", "original": "...", "rewritten": "...", "changes": [...]},\n'
            '    {"name": "Projects", "original": "", "rewritten": "...", "changes": [{"type": "add", "before": "", "after": "..."}]}\n'
            "  ],\n"
            '  "ats_score_before": 45,\n'
            '  "ats_score_after": 82,\n'
            '  "keywords_added": ["keyword1", "keyword2"],\n'
            '  "summary": "Brief description of changes made"\n'
            "}\n"
        )
        resp = _gemini.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.3,
            ),
        )
        raw = resp.text.strip() if resp.text else "{}"
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

        result = json.loads(raw)

        # Ensure required keys exist
        result.setdefault("sections", [])
        result.setdefault("ats_score_before", 0)
        result.setdefault("ats_score_after", 0)
        result.setdefault("keywords_added", [])
        result.setdefault("summary", "Resume optimized for target role")

        return result

    except json.JSONDecodeError:
        logger.error("[resume_rewriter] Failed to parse Gemini JSON response")
        return {
            "sections": [],
            "ats_score_before": 0,
            "ats_score_after": 0,
            "keywords_added": [],
            "summary": "Rewrite failed — could not parse AI response",
            "error": "JSON parse error",
        }
    except Exception as e:
        logger.error(f"[resume_rewriter] Rewrite error: {e}")
        return {
            "sections": [],
            "ats_score_before": 0,
            "ats_score_after": 0,
            "keywords_added": [],
            "summary": f"Rewrite failed: {str(e)[:200]}",
            "error": str(e),
        }


async def stream_rewrite_edits(
    resume_text: str,
    jd_text: str,
    job_title: str = "",
    company_name: str = "",
    github_data: Optional[dict] = None,
) -> AsyncGenerator[dict, None]:
    """Stream individual edit operations for real-time display.

    Yields dicts like:
      {"type": "keyword_extraction", "data": {"keywords": [...]}}
      {"type": "section_start", "data": {"name": "Summary"}}
      {"type": "edit", "data": {"section": "Summary", "change": {...}}}
      {"type": "score_update", "data": {"before": 45, "after": 72}}
      {"type": "complete", "data": {"summary": "..."}}
    """
    # Step 1: Extract keywords
    yield {"type": "status", "data": {"message": "Extracting ATS keywords from job description..."}}
    keywords = await extract_ats_keywords(jd_text)
    yield {"type": "keyword_extraction", "data": {"keywords": keywords}}

    await asyncio.sleep(0.3)

    # Step 2: Full rewrite
    yield {"type": "status", "data": {"message": "Analyzing resume against job requirements..."}}
    result = await rewrite_resume_for_jd(
        resume_text, jd_text, job_title, company_name, github_data
    )

    if result.get("error"):
        yield {"type": "error", "data": {"message": result["error"]}}
        return

    # Step 3: Stream sections
    for section in result.get("sections", []):
        yield {"type": "section_start", "data": {"name": section["name"]}}
        await asyncio.sleep(0.2)

        for change in section.get("changes", []):
            yield {
                "type": "edit",
                "data": {
                    "section": section["name"],
                    "change": change,
                },
            }
            await asyncio.sleep(0.1)

    # Step 4: Score update
    yield {
        "type": "score_update",
        "data": {
            "before": result.get("ats_score_before", 0),
            "after": result.get("ats_score_after", 0),
        },
    }

    # Step 5: Complete
    yield {
        "type": "complete",
        "data": {
            "summary": result.get("summary", ""),
            "keywords_added": result.get("keywords_added", []),
            "full_result": result,
        },
    }
