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
    # AI Labs
    {"name": "Anthropic", "careers_url": "https://job-boards.greenhouse.io/anthropic", "api_url": "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs", "category": "AI Labs"},
    {"name": "OpenAI", "careers_url": "https://job-boards.greenhouse.io/openai", "api_url": "https://boards-api.greenhouse.io/v1/boards/openai/jobs", "category": "AI Labs"},
    {"name": "Mistral", "careers_url": "https://jobs.lever.co/mistral", "category": "AI Labs"},
    {"name": "Cohere", "careers_url": "https://jobs.lever.co/cohere", "category": "AI Labs"},
    {"name": "LangChain", "careers_url": "https://jobs.ashbyhq.com/langchain", "category": "AI Labs"},
    {"name": "Pinecone", "careers_url": "https://jobs.ashbyhq.com/pinecone", "category": "AI Labs"},

    # Voice AI
    {"name": "ElevenLabs", "careers_url": "https://jobs.ashbyhq.com/elevenlabs", "category": "Voice AI"},
    {"name": "PolyAI", "careers_url": "https://jobs.lever.co/polyai", "category": "Voice AI"},
    {"name": "Hume AI", "careers_url": "https://jobs.ashbyhq.com/hume", "category": "Voice AI"},
    {"name": "Deepgram", "careers_url": "https://jobs.ashbyhq.com/deepgram", "category": "Voice AI"},
    {"name": "Vapi", "careers_url": "https://jobs.ashbyhq.com/vapi", "category": "Voice AI"},

    # AI Platforms
    {"name": "Retool", "careers_url": "https://jobs.ashbyhq.com/retool", "category": "AI Platforms"},
    {"name": "Vercel", "careers_url": "https://job-boards.greenhouse.io/vercel", "api_url": "https://boards-api.greenhouse.io/v1/boards/vercel/jobs", "category": "AI Platforms"},
    {"name": "Temporal", "careers_url": "https://jobs.ashbyhq.com/temporal", "category": "AI Platforms"},
    {"name": "Glean", "careers_url": "https://jobs.ashbyhq.com/glean", "category": "AI Platforms"},
    {"name": "Arize AI", "careers_url": "https://jobs.lever.co/arize", "category": "AI Platforms"},
    {"name": "Airtable", "careers_url": "https://job-boards.greenhouse.io/airtable", "api_url": "https://boards-api.greenhouse.io/v1/boards/airtable/jobs", "category": "AI Platforms"},

    # Contact Center AI
    {"name": "Ada", "careers_url": "https://jobs.lever.co/ada-support", "category": "Contact Center"},
    {"name": "Sierra", "careers_url": "https://jobs.ashbyhq.com/sierra", "category": "Contact Center"},
    {"name": "Decagon", "careers_url": "https://jobs.ashbyhq.com/decagon", "category": "Contact Center"},

    # Enterprise
    {"name": "Salesforce", "careers_url": "https://job-boards.greenhouse.io/salesforce", "api_url": "https://boards-api.greenhouse.io/v1/boards/salesforce/jobs", "category": "Enterprise"},
    {"name": "Twilio", "careers_url": "https://job-boards.greenhouse.io/twilio", "api_url": "https://boards-api.greenhouse.io/v1/boards/twilio/jobs", "category": "Enterprise"},
    {"name": "Gong", "careers_url": "https://jobs.lever.co/gong", "category": "Enterprise"},
    {"name": "Dialpad", "careers_url": "https://job-boards.greenhouse.io/dialpad", "api_url": "https://boards-api.greenhouse.io/v1/boards/dialpad/jobs", "category": "Enterprise"},

    # LLMOps
    {"name": "Langfuse", "careers_url": "https://jobs.ashbyhq.com/langfuse", "category": "LLMOps"},
    {"name": "Weights & Biases", "careers_url": "https://jobs.lever.co/wandb", "category": "LLMOps"},
    {"name": "Lindy", "careers_url": "https://jobs.ashbyhq.com/lindy", "category": "LLMOps"},
    {"name": "Cognigy", "careers_url": "https://job-boards.greenhouse.io/cognigy", "api_url": "https://boards-api.greenhouse.io/v1/boards/cognigy/jobs", "category": "LLMOps"},

    # Automation
    {"name": "n8n", "careers_url": "https://jobs.ashbyhq.com/n8n", "category": "Automation"},
    {"name": "Zapier", "careers_url": "https://job-boards.greenhouse.io/zapier", "api_url": "https://boards-api.greenhouse.io/v1/boards/zapier/jobs", "category": "Automation"},

    # European
    {"name": "Factorial", "careers_url": "https://jobs.ashbyhq.com/factorial", "category": "European"},
    {"name": "Attio", "careers_url": "https://jobs.ashbyhq.com/attio", "category": "European"},
    {"name": "Tinybird", "careers_url": "https://jobs.ashbyhq.com/tinybird", "category": "European"},
    {"name": "Travelperk", "careers_url": "https://jobs.ashbyhq.com/travelperk", "category": "European"},

    # Developer Tools
    {"name": "Supabase", "careers_url": "https://jobs.ashbyhq.com/supabase", "category": "DevTools"},
    {"name": "Railway", "careers_url": "https://jobs.ashbyhq.com/railway", "category": "DevTools"},
    {"name": "Render", "careers_url": "https://jobs.lever.co/render", "category": "DevTools"},
    {"name": "Fly.io", "careers_url": "https://jobs.ashbyhq.com/fly.io", "category": "DevTools"},
    {"name": "Replit", "careers_url": "https://jobs.ashbyhq.com/replit", "category": "DevTools"},
    {"name": "Neon", "careers_url": "https://jobs.ashbyhq.com/neon", "category": "DevTools"},

    # Security / Infra
    {"name": "Wiz", "careers_url": "https://jobs.lever.co/wiz", "category": "Security"},
    {"name": "Snyk", "careers_url": "https://job-boards.greenhouse.io/snyk", "api_url": "https://boards-api.greenhouse.io/v1/boards/snyk/jobs", "category": "Security"},
    {"name": "Datadog", "careers_url": "https://job-boards.greenhouse.io/datadog", "api_url": "https://boards-api.greenhouse.io/v1/boards/datadog/jobs", "category": "Security"},

    # Fintech
    {"name": "Stripe", "careers_url": "https://job-boards.greenhouse.io/stripe", "api_url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs", "category": "Fintech"},
    {"name": "Ramp", "careers_url": "https://jobs.ashbyhq.com/ramp", "category": "Fintech"},
    {"name": "Brex", "careers_url": "https://job-boards.greenhouse.io/brex", "api_url": "https://boards-api.greenhouse.io/v1/boards/brex/jobs", "category": "Fintech"},
]

DEFAULT_TITLE_FILTER = {
    "positive": [
        "ai", "machine learning", "ml", "data scientist", "nlp",
        "llm", "deep learning", "computer vision", "generative",
        "engineer", "developer", "architect", "platform",
        "product manager", "technical program", "devops", "sre",
        "backend", "frontend", "fullstack", "full-stack", "software",
    ],
    "negative": [
        "intern", "internship", "co-op", "junior designer",
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
