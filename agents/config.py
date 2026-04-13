"""Shared configuration for the agent suite.

Reads API keys from the project-root .env (same keys as existing backend).
All paths are relative to the agents/ directory.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── Load .env from project root ─────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH)

# ── Directory layout ─────────────────────────────────────────────────
AGENTS_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENTS_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
OUTPUT_DIR = DATA_DIR / "output"
TEMPLATES_DIR = AGENTS_DIR / "templates"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── API Keys ─────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── LLM Model Config ────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-2.0-flash"

# ── Rate Limits ──────────────────────────────────────────────────────
GROQ_RPM_LIMIT = 25        # requests/min (below 30 free-tier max)
GEMINI_RPM_LIMIT = 60      # requests/min (conservative for long-context)
GROQ_MAX_TOKENS = 2048     # max output tokens per Groq call
GEMINI_MAX_TOKENS = 4096   # max output tokens per Gemini call

# ── Scanner Config ───────────────────────────────────────────────────
SCAN_CONCURRENCY = 10       # parallel HTTP fetches for portal scanning
SCAN_FETCH_TIMEOUT = 10     # seconds per HTTP request
SCAN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# ── Batch Config ─────────────────────────────────────────────────────
BATCH_MAX_CONCURRENCY = 5   # parallel workers for batch processing
BATCH_MAX_RETRIES = 2       # retries per failed URL
BATCH_STATE_FILE = DATA_DIR / "batch_state.tsv"

# ── Tracker Config ───────────────────────────────────────────────────
APPLICATIONS_FILE = DATA_DIR / "applications.md"
PIPELINE_FILE = DATA_DIR / "pipeline.md"
SCAN_HISTORY_FILE = DATA_DIR / "scan_history.tsv"

# ── Scoring Config ───────────────────────────────────────────────────
MIN_APPLY_SCORE = 4.0       # minimum score to recommend applying
AUTO_PDF_SCORE = 4.0        # auto-generate PDF for scores above this

# ── Canonical Statuses ───────────────────────────────────────────────
STATUSES = [
    "Evaluated",
    "Applied",
    "Responded",
    "Interview",
    "Offer",
    "Rejected",
    "Discarded",
    "SKIP",
]


def validate_config() -> list[str]:
    """Check configuration and return list of warnings."""
    warnings = []
    if not GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY not set — Gemini-powered agents will fail")
    if not GROQ_API_KEY:
        warnings.append("GROQ_API_KEY not set — Groq-powered agents will fail")
    return warnings
