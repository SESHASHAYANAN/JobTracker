"""Portal registry and API detection for 45+ career portals.

Ported from career-ops scan.mjs detectApi() + portals.example.yml.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from agents.models import PortalConfig, TitleFilterConfig


# ── Default portals (45+ companies from career-ops) ─────────────────

DEFAULT_PORTALS: list[dict] = [
    # ── AI Labs ── (all verified ✅ via direct HTTP 200)
    {"name": "Anthropic", "careers_url": "https://job-boards.greenhouse.io/anthropic", "api_url": "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs", "category": "AI Labs"},
    {"name": "OpenAI", "careers_url": "https://jobs.ashbyhq.com/openai", "api_url": "https://api.ashbyhq.com/posting-api/job-board/openai?includeCompensation=true", "category": "AI Labs"},
    {"name": "Cohere", "careers_url": "https://jobs.ashbyhq.com/cohere", "api_url": "https://api.ashbyhq.com/posting-api/job-board/cohere?includeCompensation=true", "category": "AI Labs"},
    {"name": "LangChain", "careers_url": "https://jobs.ashbyhq.com/langchain", "category": "AI Labs"},
    {"name": "Pinecone", "careers_url": "https://jobs.ashbyhq.com/pinecone", "category": "AI Labs"},
    {"name": "Mistral", "careers_url": "https://jobs.lever.co/mistral", "category": "AI Labs"},

    # ── Voice AI ── (verified ✅)
    {"name": "ElevenLabs", "careers_url": "https://jobs.ashbyhq.com/elevenlabs", "category": "Voice AI"},
    {"name": "Deepgram", "careers_url": "https://jobs.ashbyhq.com/deepgram", "category": "Voice AI"},
    {"name": "Vapi", "careers_url": "https://jobs.ashbyhq.com/vapi", "category": "Voice AI"},

    # ── AI / Design Platforms ── (verified ✅)
    {"name": "Retool", "careers_url": "https://jobs.ashbyhq.com/retool", "category": "AI Platforms"},
    {"name": "Vercel", "careers_url": "https://job-boards.greenhouse.io/vercel", "api_url": "https://boards-api.greenhouse.io/v1/boards/vercel/jobs", "category": "AI Platforms"},
    {"name": "Temporal", "careers_url": "https://jobs.ashbyhq.com/temporal", "category": "AI Platforms"},
    {"name": "Airtable", "careers_url": "https://job-boards.greenhouse.io/airtable", "api_url": "https://boards-api.greenhouse.io/v1/boards/airtable/jobs", "category": "AI Platforms"},
    {"name": "Figma", "careers_url": "https://job-boards.greenhouse.io/figma", "api_url": "https://boards-api.greenhouse.io/v1/boards/figma/jobs", "category": "AI Platforms"},
    {"name": "Discord", "careers_url": "https://job-boards.greenhouse.io/discord", "api_url": "https://boards-api.greenhouse.io/v1/boards/discord/jobs", "category": "AI Platforms"},

    # ── Contact Center AI ── (verified ✅)
    {"name": "Sierra", "careers_url": "https://jobs.ashbyhq.com/sierra", "category": "Contact Center"},
    {"name": "Decagon", "careers_url": "https://jobs.ashbyhq.com/decagon", "category": "Contact Center"},

    # ── Enterprise ── (verified ✅)
    {"name": "Twilio", "careers_url": "https://job-boards.greenhouse.io/twilio", "api_url": "https://boards-api.greenhouse.io/v1/boards/twilio/jobs", "category": "Enterprise"},
    {"name": "Gong", "careers_url": "https://job-boards.greenhouse.io/gongio", "api_url": "https://boards-api.greenhouse.io/v1/boards/gongio/jobs", "category": "Enterprise"},
    {"name": "Dialpad", "careers_url": "https://job-boards.greenhouse.io/dialpad", "api_url": "https://boards-api.greenhouse.io/v1/boards/dialpad/jobs", "category": "Enterprise"},
    {"name": "Gusto", "careers_url": "https://job-boards.greenhouse.io/gusto", "api_url": "https://boards-api.greenhouse.io/v1/boards/gusto/jobs", "category": "Enterprise"},

    # ── LLMOps / AI Infra ── (verified ✅)
    {"name": "Langfuse", "careers_url": "https://jobs.ashbyhq.com/langfuse", "category": "LLMOps"},
    {"name": "Lindy", "careers_url": "https://jobs.ashbyhq.com/lindy", "category": "LLMOps"},

    # ── Automation ── (verified ✅)
    {"name": "n8n", "careers_url": "https://jobs.ashbyhq.com/n8n", "category": "Automation"},
    {"name": "Zapier", "careers_url": "https://jobs.ashbyhq.com/zapier", "api_url": "https://api.ashbyhq.com/posting-api/job-board/zapier?includeCompensation=true", "category": "Automation"},

    # ── European ── (verified ✅)
    {"name": "Attio", "careers_url": "https://jobs.ashbyhq.com/attio", "category": "European"},
    {"name": "Tinybird", "careers_url": "https://jobs.lever.co/tinybird", "category": "European"},
    {"name": "Travelperk", "careers_url": "https://jobs.ashbyhq.com/perk", "api_url": "https://api.ashbyhq.com/posting-api/job-board/perk?includeCompensation=true", "category": "European"},

    # ── Developer Tools ── (verified ✅)
    {"name": "Supabase", "careers_url": "https://jobs.ashbyhq.com/supabase", "category": "DevTools"},
    {"name": "Railway", "careers_url": "https://jobs.ashbyhq.com/railway", "category": "DevTools"},
    {"name": "Render", "careers_url": "https://jobs.ashbyhq.com/render", "api_url": "https://api.ashbyhq.com/posting-api/job-board/render?includeCompensation=true", "category": "DevTools"},
    {"name": "Replit", "careers_url": "https://jobs.ashbyhq.com/replit", "category": "DevTools"},
    {"name": "Neon", "careers_url": "https://jobs.ashbyhq.com/neon", "category": "DevTools"},
    {"name": "GitLab", "careers_url": "https://job-boards.greenhouse.io/gitlab", "api_url": "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs", "category": "DevTools"},
    {"name": "Sourcegraph", "careers_url": "https://job-boards.greenhouse.io/sourcegraph91", "api_url": "https://boards-api.greenhouse.io/v1/boards/sourcegraph91/jobs", "category": "DevTools"},

    # ── Security / Infra ── (verified ✅)
    {"name": "Wiz", "careers_url": "https://jobs.ashbyhq.com/wiz", "api_url": "https://api.ashbyhq.com/posting-api/job-board/wiz?includeCompensation=true", "category": "Security"},
    {"name": "Snyk", "careers_url": "https://jobs.ashbyhq.com/snyk", "api_url": "https://api.ashbyhq.com/posting-api/job-board/snyk?includeCompensation=true", "category": "Security"},
    {"name": "Datadog", "careers_url": "https://job-boards.greenhouse.io/datadog", "api_url": "https://boards-api.greenhouse.io/v1/boards/datadog/jobs", "category": "Security"},
    {"name": "Cloudflare", "careers_url": "https://job-boards.greenhouse.io/cloudflare", "api_url": "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs", "category": "Security"},
    {"name": "CockroachDB", "careers_url": "https://job-boards.greenhouse.io/cockroachlabs", "api_url": "https://boards-api.greenhouse.io/v1/boards/cockroachlabs/jobs", "category": "Security"},

    # ── Fintech ── (verified ✅)
    {"name": "Stripe", "careers_url": "https://job-boards.greenhouse.io/stripe", "api_url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs", "category": "Fintech"},
    {"name": "Ramp", "careers_url": "https://jobs.ashbyhq.com/ramp", "category": "Fintech"},
    {"name": "Brex", "careers_url": "https://job-boards.greenhouse.io/brex", "api_url": "https://boards-api.greenhouse.io/v1/boards/brex/jobs", "category": "Fintech"},
    {"name": "Duolingo", "careers_url": "https://job-boards.greenhouse.io/duolingo", "api_url": "https://boards-api.greenhouse.io/v1/boards/duolingo/jobs", "category": "Fintech"},

    # ── Indian Startups ── (verified working ✅)
    {"name": "Postman", "careers_url": "https://job-boards.greenhouse.io/postman", "api_url": "https://boards-api.greenhouse.io/v1/boards/postman/jobs", "category": "India"},
    {"name": "CRED", "careers_url": "https://jobs.lever.co/cred", "category": "India"},
    {"name": "Meesho", "careers_url": "https://jobs.lever.co/meesho", "category": "India"},
]

DEFAULT_TITLE_FILTER = {
    "positive": [
        "ai", "machine learning", "ml", "data scientist", "nlp",
        "llm", "deep learning", "computer vision", "generative",
        "engineer", "developer", "architect", "platform",
        "product manager", "technical program", "devops", "sre",
        "backend", "frontend", "fullstack", "full-stack", "software",
        "intern", "fresher", "new grad", "graduate", "entry",
    ],
    "negative": [
        "receptionist", "office manager", "janitor",
        "legal counsel", "general counsel", "paralegal",
    ],
    "seniority_boost": [
        "senior", "staff", "principal", "lead", "head of", "director", "vp",
    ],
}


def detect_api(portal: PortalConfig) -> Optional[dict]:
    """Detect the ATS API type and URL from a portal config.

    Ported from career-ops scan.mjs detectApi().
    """
    # Explicit API URL
    if portal.api_url:
        if "greenhouse" in portal.api_url:
            return {"type": "greenhouse", "url": portal.api_url}
        elif "ashby" in portal.api_url:
            return {"type": "ashby", "url": portal.api_url}
        elif "lever" in portal.api_url:
            return {"type": "lever", "url": portal.api_url}

    url = portal.careers_url or ""

    # Ashby: jobs.ashbyhq.com/{slug}
    ashby_match = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)", url)
    if ashby_match:
        slug = ashby_match.group(1)
        return {
            "type": "ashby",
            "url": f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
        }

    # Lever: jobs.lever.co/{slug}
    lever_match = re.search(r"jobs\.lever\.co/([^/?#]+)", url)
    if lever_match:
        slug = lever_match.group(1)
        return {
            "type": "lever",
            "url": f"https://api.lever.co/v0/postings/{slug}",
        }

    # Greenhouse: job-boards.greenhouse.io/{slug} or job-boards.eu.greenhouse.io/{slug}
    gh_match = re.search(r"job-boards(?:\.eu)?\.greenhouse\.io/([^/?#]+)", url)
    if gh_match:
        slug = gh_match.group(1)
        return {
            "type": "greenhouse",
            "url": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        }

    return None


def load_portals_config(config_path: Optional[Path] = None) -> dict:
    """Load portal configuration from YAML or use defaults.

    Returns dict with keys: 'portals' (list[PortalConfig]), 'title_filter' (TitleFilterConfig).
    """
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        portals = [
            PortalConfig(**p) for p in raw.get("tracked_companies", [])
        ]
        tf_raw = raw.get("title_filter", {})
        title_filter = TitleFilterConfig(
            positive=tf_raw.get("positive", []),
            negative=tf_raw.get("negative", []),
            seniority_boost=tf_raw.get("seniority_boost", []),
        )
    else:
        portals = [PortalConfig(**p) for p in DEFAULT_PORTALS]
        title_filter = TitleFilterConfig(**DEFAULT_TITLE_FILTER)

    return {"portals": portals, "title_filter": title_filter}
