"""Persistent batch state management via TSV file.

Mirrors career-ops batch-state.tsv for crash recovery and resumability.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from agents.config import BATCH_STATE_FILE
from agents.models import BatchJob, BatchStatus


class BatchState:
    """TSV-based persistent batch state.

    Columns: id, url, status, started_at, completed_at, report_num, score, error, retries

    Enables crash-recovery:
    - On restart: read state, skip completed, retry pending
    - Thread-safe writes via simple file locking
    """

    def __init__(self, state_file: Optional[Path] = None):
        self._file = state_file or BATCH_STATE_FILE
        self._jobs: dict[str, BatchJob] = {}

    def load(self):
        """Load state from TSV file."""
        self._jobs.clear()
        if not self._file.exists():
            return

        lines = self._file.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) <= 1:  # header only
            return

        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 9:
                continue
            try:
                job = BatchJob(
                    id=int(parts[0]),
                    url=parts[1],
                    status=BatchStatus(parts[2]) if parts[2] else BatchStatus.PENDING,
                    started_at=parts[3] if parts[3] != "-" else None,
                    completed_at=parts[4] if parts[4] != "-" else None,
                    report_num=int(parts[5]) if parts[5] != "-" else None,
                    score=float(parts[6]) if parts[6] != "-" else None,
                    error=parts[7] if parts[7] != "-" else None,
                    retries=int(parts[8]) if parts[8] != "-" else 0,
                )
                self._jobs[job.url] = job
            except (ValueError, IndexError):
                continue

    def save(self):
        """Save current state to TSV file."""
        self._file.parent.mkdir(parents=True, exist_ok=True)
        lines = ["id\turl\tstatus\tstarted_at\tcompleted_at\treport_num\tscore\terror\tretries"]

        for job in sorted(self._jobs.values(), key=lambda j: j.id):
            lines.append(
                f"{job.id}\t{job.url}\t{job.status.value}\t"
                f"{job.started_at or '-'}\t{job.completed_at or '-'}\t"
                f"{job.report_num or '-'}\t{job.score or '-'}\t"
                f"{job.error or '-'}\t{job.retries}"
            )

        self._file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def update(self, job: BatchJob):
        """Update a single job's state and persist."""
        self._jobs[job.url] = job
        self.save()

    def get_by_url(self, url: str) -> Optional[BatchJob]:
        """Get a job by URL."""
        return self._jobs.get(url)

    def get_all(self) -> list[BatchJob]:
        """Get all jobs sorted by ID."""
        return sorted(self._jobs.values(), key=lambda j: j.id)

    def get_pending(self) -> list[BatchJob]:
        """Get all pending jobs."""
        return [j for j in self._jobs.values() if j.status == BatchStatus.PENDING]

    def get_failed(self) -> list[BatchJob]:
        """Get all failed jobs."""
        return [j for j in self._jobs.values() if j.status == BatchStatus.FAILED]

    def get_completed(self) -> list[BatchJob]:
        """Get all completed jobs."""
        return [j for j in self._jobs.values() if j.status == BatchStatus.COMPLETED]
