"""Markdown-table persistence for the application tracker.

Reads and writes applications.md in the career-ops format:
| # | Date | Company | Role | Score | Status | PDF | Report | Notes |
"""
from __future__ import annotations

import re
from typing import Optional

from agents.config import APPLICATIONS_FILE
from agents.models import PipelineEntry, JobStatus


class TrackerStore:
    """Markdown-table persistence for applications.md.

    Format (matching career-ops):
    | # | Date | Company | Role | Score | Status | PDF | Report | Notes |

    Canonical statuses: Evaluated, Applied, Responded, Interview, 
    Offer, Rejected, Discarded, SKIP
    """

    def __init__(self):
        self._entries: list[PipelineEntry] = []

    def load(self):
        """Load entries from applications.md."""
        self._entries.clear()

        if not APPLICATIONS_FILE.exists():
            return

        text = APPLICATIONS_FILE.read_text(encoding="utf-8")
        lines = text.strip().split("\n")

        for line in lines:
            # Match markdown table rows (skip header and separator)
            if not line.startswith("|") or "---" in line:
                continue

            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]  # remove empty

            if len(parts) < 6 or parts[0] == "#":
                continue

            try:
                number = int(parts[0])
            except ValueError:
                continue

            try:
                score_str = parts[4].replace("/5", "").strip()
                score = float(score_str) if score_str and score_str != "-" else None
            except (ValueError, IndexError):
                score = None

            try:
                status = JobStatus(parts[5].strip())
            except (ValueError, IndexError):
                status = JobStatus.EVALUATED

            pdf_generated = "✅" in (parts[6] if len(parts) > 6 else "")
            report_link = parts[7] if len(parts) > 7 else None
            notes = parts[8] if len(parts) > 8 else ""

            self._entries.append(PipelineEntry(
                number=number,
                date=parts[1].strip(),
                company=parts[2].strip(),
                role=parts[3].strip(),
                score=score,
                status=status,
                pdf_generated=pdf_generated,
                report_link=report_link,
                notes=notes,
            ))

    def save(self):
        """Save all entries to applications.md."""
        APPLICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Applications Tracker\n",
            "| # | Date | Company | Role | Score | Status | PDF | Report | Notes |",
            "|---|------|---------|------|-------|--------|-----|--------|-------|",
        ]

        for e in sorted(self._entries, key=lambda x: x.number):
            pdf_icon = "✅" if e.pdf_generated else "❌"
            score_str = f"{e.score:.1f}/5" if e.score else "-"
            report_str = e.report_link or "-"
            lines.append(
                f"| {e.number} | {e.date} | {e.company} | {e.role} | "
                f"{score_str} | {e.status.value} | {pdf_icon} | {report_str} | {e.notes} |"
            )

        APPLICATIONS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def add(self, entry: PipelineEntry):
        """Add a new entry and save."""
        # Auto-assign number if not set
        if entry.number <= 0:
            existing_nums = [e.number for e in self._entries]
            entry.number = max(existing_nums, default=0) + 1
        self._entries.append(entry)
        self.save()

    def update(self, entry: PipelineEntry):
        """Update an existing entry by number."""
        for i, e in enumerate(self._entries):
            if e.number == entry.number:
                self._entries[i] = entry
                break
        self.save()

    def find(self, company: str, role: str) -> Optional[PipelineEntry]:
        """Find an entry by company + role (case-insensitive)."""
        for e in self._entries:
            if (e.company.lower() == company.lower() and
                    e.role.lower() == role.lower()):
                return e
        return None

    def get_all(self) -> list[PipelineEntry]:
        """Get all entries sorted by number."""
        return sorted(self._entries, key=lambda x: x.number)

    def get_next_number(self) -> int:
        """Get the next available entry number."""
        existing = [e.number for e in self._entries]
        return max(existing, default=0) + 1
