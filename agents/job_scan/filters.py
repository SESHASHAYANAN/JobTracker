"""Title filtering and deduplication for the scanner.

Ported from career-ops scan.mjs buildTitleFilter/loadSeenUrls/loadSeenCompanyRoles.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Set

from agents.config import SCAN_HISTORY_FILE, PIPELINE_FILE, APPLICATIONS_FILE


class TitleFilter:
    """Configurable title filter with positive and negative keywords.

    A job title passes if:
    - At least one positive keyword is found (case-insensitive), AND
    - No negative keywords are found.

    If no positive keywords are configured, all titles pass (only negative filter applies).
    """

    def __init__(self, positive: list[str], negative: list[str]):
        self._positive = [k.lower() for k in positive]
        self._negative = [k.lower() for k in negative]

    def matches(self, title: str) -> bool:
        """Check if a job title passes the filter."""
        lower = title.lower()

        # Positive check: at least one keyword must match (if any are configured)
        if self._positive:
            has_positive = any(k in lower for k in self._positive)
            if not has_positive:
                return False

        # Negative check: no keyword must match
        has_negative = any(k in lower for k in self._negative)
        if has_negative:
            return False

        return True


class Deduplicator:
    """Deduplicates job listings against three sources:

    1. scan_history.tsv — URL exact match (already seen)
    2. pipeline.md — URL exact match (already in inbox)
    3. applications.md — company+role normalized match (already evaluated)

    Ported from career-ops scan.mjs loadSeenUrls/loadSeenCompanyRoles.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._seen_urls: Set[str] = set()
        self._seen_company_roles: Set[str] = set()

    def load(self):
        """Load dedup sets from all three sources."""
        self._seen_urls.clear()
        self._seen_company_roles.clear()
        self._load_scan_history()
        self._load_pipeline()
        self._load_applications()

    def is_seen(self, url: str, company: str, title: str) -> bool:
        """Check if a job has already been seen."""
        if url in self._seen_urls:
            return True
        key = f"{company.lower()}::{title.lower()}"
        if key in self._seen_company_roles:
            return True
        return False

    def mark_seen(self, url: str, company: str, title: str):
        """Mark a job as seen (for intra-scan dedup)."""
        self._seen_urls.add(url)
        self._seen_company_roles.add(f"{company.lower()}::{title.lower()}")

    def _load_scan_history(self):
        """Load seen URLs from scan_history.tsv."""
        path = SCAN_HISTORY_FILE
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8").split("\n")
        for line in lines[1:]:  # skip header
            parts = line.split("\t")
            if parts and parts[0]:
                self._seen_urls.add(parts[0])

    def _load_pipeline(self):
        """Load seen URLs from pipeline.md checkbox lines."""
        path = PIPELINE_FILE
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"- \[[ x]\] (https?://\S+)", text):
            self._seen_urls.add(match.group(1))

    def _load_applications(self):
        """Load seen company+role from applications.md.

        Also extracts any inline URLs.
        """
        path = APPLICATIONS_FILE
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")

        # Extract URLs
        for match in re.finditer(r"https?://[^\s|)]+", text):
            self._seen_urls.add(match.group(0))

        # Extract company+role pairs from markdown table rows
        # Format: | # | Date | Company | Role | ...
        for match in re.finditer(
            r"\|[^|]+\|[^|]+\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", text
        ):
            company = match.group(1).strip().lower()
            role = match.group(2).strip().lower()
            if company and role and company != "company":
                self._seen_company_roles.add(f"{company}::{role}")
