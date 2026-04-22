"""TrackerAgent — application pipeline status tracking.

Manages applications.md with status tracking, report linking, and analytics.
"""
from __future__ import annotations

from typing import Optional

from agents.models import PipelineEntry, TrackerSummary, PipelineAnalytics, JobStatus
from agents.tracker.store import TrackerStore
from agents.tracker.analytics import compute_analytics


class TrackerAgent:
    """Application pipeline status tracker.

    Manages the canonical application tracker (applications.md) with:
    - Status tracking: Evaluated → Applied → Interview → Offer/Rejected
    - Report linking: each entry links to its evaluation report
    - PDF tracking: ✅/❌ for CV generation status
    - Dedup: never creates duplicate company+role entries
    - Analytics: success rates, stage conversion, scoring patterns
    """

    def __init__(self):
        self._store = TrackerStore()

    async def add_entry(self, entry: PipelineEntry) -> None:
        """Add a new entry to the tracker.

        If company+role already exists, updates the existing entry instead.
        """
        self._store.load()

        # Check for existing entry (dedup)
        existing = self._store.find(entry.company, entry.role)
        if existing:
            # Update existing entry
            existing.score = entry.score or existing.score
            existing.status = entry.status
            existing.pdf_generated = entry.pdf_generated or existing.pdf_generated
            existing.report_link = entry.report_link or existing.report_link
            existing.notes = entry.notes or existing.notes
            self._store.update(existing)
            print(f"  [tracker] Updated: {entry.company} - {entry.role} -> {entry.status.value}")
        else:
            # Add new entry
            self._store.add(entry)
            print(f"  [tracker] Added: {entry.company} - {entry.role} (#{entry.number})")

    async def update_status(
        self, company: str, role: str, new_status: str
    ) -> bool:
        """Update the status of an existing entry.

        Returns True if found and updated, False otherwise.
        """
        self._store.load()
        existing = self._store.find(company, role)
        if not existing:
            print(f"  [tracker] Not found: {company} - {role}")
            return False

        try:
            existing.status = JobStatus(new_status)
        except ValueError:
            print(f"  [tracker] Invalid status: {new_status}")
            print(f"  [tracker] Valid statuses: {', '.join(s.value for s in JobStatus)}")
            return False

        self._store.update(existing)
        print(f"  [tracker] Updated: {company} - {role} -> {new_status}")
        return True

    async def get_summary(self) -> TrackerSummary:
        """Get summary statistics for the pipeline."""
        self._store.load()
        entries = self._store.get_all()

        if not entries:
            return TrackerSummary()

        # Count by status
        by_status: dict[str, int] = {}
        scores = []
        companies = []

        for e in entries:
            status_val = e.status.value
            by_status[status_val] = by_status.get(status_val, 0) + 1
            if e.score:
                scores.append(e.score)
            companies.append(e.company)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Top companies by count
        from collections import Counter
        top = Counter(companies).most_common(5)
        top_companies = [c for c, _ in top]

        return TrackerSummary(
            total_entries=len(entries),
            by_status=by_status,
            avg_score=round(avg_score, 2),
            top_companies=top_companies,
            last_updated=entries[-1].date if entries else None,
        )

    async def get_analytics(self) -> PipelineAnalytics:
        """Get detailed pipeline analytics."""
        self._store.load()
        entries = self._store.get_all()
        summary = await self.get_summary()
        return compute_analytics(entries, summary)

    def get_entries(
        self, status: Optional[str] = None
    ) -> list[PipelineEntry]:
        """Get all entries, optionally filtered by status."""
        self._store.load()
        entries = self._store.get_all()
        if status:
            entries = [e for e in entries if e.status.value == status]
        return entries

    async def print_status(self):
        """Print a formatted pipeline status table."""
        self._store.load()
        entries = self._store.get_all()
        summary = await self.get_summary()

        sep = "=" * 85
        print(f"\n{sep}")
        print("Application Pipeline Status")
        print(sep)

        if not entries:
            print("No applications tracked yet.")
            print(f"\n-> Run 'python -m agents.cli scan' to find jobs, then score them.")
            return

        # Print table header
        print(f"{'#':>3} | {'Date':^10} | {'Company':^18} | {'Role':^22} | {'Score':^5} | {'Status':^10} | {'PDF':^3}")
        print("-" * 85)

        for e in entries:
            pdf_icon = "Y" if e.pdf_generated else "N"
            score_str = f"{e.score:.1f}" if e.score else "  - "
            print(
                f"{e.number:>3} | {e.date:^10} | {e.company[:18]:^18} | "
                f"{e.role[:22]:^22} | {score_str:^5} | {e.status.value:^10} | {pdf_icon:^3}"
            )

        print("-" * 85)
        print(f"\nTotal: {summary.total_entries} | "
              f"Avg Score: {summary.avg_score:.1f}/5.0 | "
              f"Status: {', '.join(f'{k}: {v}' for k, v in summary.by_status.items())}")
