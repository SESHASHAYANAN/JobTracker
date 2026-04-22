"""ATS compliance checker and optimizer.

Ensures CVs pass ATS parsing rules from career-ops pdf.md.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from agents.models import TailoredSection


class ATSOptimizer:
    """Ensures CV passes ATS parsing rules.

    Checks (from career-ops pdf.md):
    - Single-column layout (no sidebars)
    - Standard section headers
    - No text in images/SVGs
    - UTF-8, selectable text
    - Unicode normalization (em-dashes → hyphens, smart quotes → straight)
    - Keywords distributed across sections
    """

    # Standard ATS-friendly section headers
    STANDARD_HEADERS = {
        "Professional Summary", "Summary", "Profile",
        "Work Experience", "Experience", "Employment History",
        "Education", "Academic Background",
        "Skills", "Technical Skills", "Core Competencies",
        "Certifications", "Certificates",
        "Projects", "Portfolio",
    }

    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters for ATS compatibility.

        Replaces:
        - Em-dashes (—) → hyphens (-)
        - En-dashes (–) → hyphens (-)
        - Smart quotes (" " ' ') → straight quotes (" ')
        - Zero-width characters → removed
        - Non-breaking spaces → regular spaces
        """
        replacements = {
            "\u2014": "-",   # em-dash
            "\u2013": "-",   # en-dash
            "\u2018": "'",   # left single quote
            "\u2019": "'",   # right single quote
            "\u201C": '"',   # left double quote
            "\u201D": '"',   # right double quote
            "\u2026": "...", # ellipsis
            "\u00A0": " ",   # non-breaking space
            "\u200B": "",    # zero-width space
            "\u200C": "",    # zero-width non-joiner
            "\u200D": "",    # zero-width joiner
            "\uFEFF": "",    # byte order mark
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def check_section_headers(self, sections: list[TailoredSection]) -> list[str]:
        """Check that section headers are ATS-standard."""
        warnings = []
        for section in sections:
            if section.name not in self.STANDARD_HEADERS:
                closest = min(
                    self.STANDARD_HEADERS,
                    key=lambda h: self._edit_distance(section.name.lower(), h.lower()),
                )
                warnings.append(
                    f"Non-standard header '{section.name}' — consider '{closest}'"
                )
        return warnings

    def compute_keyword_coverage(
        self,
        cv_text: str,
        jd_keywords: list[str],
    ) -> tuple[float, list[str], list[str]]:
        """Compute keyword coverage percentage.

        Returns (coverage_pct, found_keywords, missing_keywords).
        """
        cv_lower = cv_text.lower()
        found = [k for k in jd_keywords if k.lower() in cv_lower]
        missing = [k for k in jd_keywords if k.lower() not in cv_lower]
        coverage = len(found) / len(jd_keywords) * 100 if jd_keywords else 0
        return round(coverage, 1), found, missing

    def compute_ats_score(
        self,
        sections: list[TailoredSection],
        all_keywords: list[str],
        found_keywords: list[str],
    ) -> float:
        """Compute an overall ATS compliance score (0-100).

        Factors:
        - Keyword coverage (40%)
        - Standard headers (20%)
        - Section completeness (20%)
        - Text quality (20%)
        """
        score = 0.0

        # Keyword coverage (40 points)
        if all_keywords:
            keyword_pct = len(found_keywords) / len(all_keywords)
            score += keyword_pct * 40

        # Standard headers (20 points)
        header_warnings = self.check_section_headers(sections)
        header_score = max(0, 20 - len(header_warnings) * 5)
        score += header_score

        # Section completeness (20 points) — core sections present
        section_names = {s.name.lower() for s in sections}
        required = {"professional summary", "work experience", "skills", "education"}
        present = required.intersection(section_names)
        score += (len(present) / len(required)) * 20

        # Text quality (20 points) — no empty sections, reasonable length
        non_empty = sum(1 for s in sections if len(s.tailored.strip()) > 20)
        if sections:
            score += (non_empty / len(sections)) * 20

        return min(score, 100.0)

    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        """Simple Levenshtein distance for header matching."""
        if len(s1) < len(s2):
            return ATSOptimizer._edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev[j + 1] + 1
                deletions = curr[j] + 1
                substitutions = prev[j] + (c1 != c2)
                curr.append(min(insertions, deletions, substitutions))
            prev = curr
        return prev[-1]
