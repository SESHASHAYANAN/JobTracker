"""BatchAgent — parallel processing of 100+ job URLs.

Replaces career-ops bash orchestrator + claude -p workers with
Python asyncio + semaphore-controlled concurrency.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents.config import BATCH_MAX_CONCURRENCY, BATCH_MAX_RETRIES, AUTO_PDF_SCORE
from agents.models import BatchJob, BatchResult, BatchStatus
from agents.batch.worker import BatchWorker
from agents.batch.state import BatchState


class BatchAgent:
    """Parallel processing of 100+ job URLs.

    Architecture (adapted from career-ops batch.md):
    - career-ops forks `claude -p` child processes (each 200K tokens)
    - We use Python asyncio with semaphore-controlled concurrency
    - Each worker gets ScoringAgent + CVTailorAgent (shared singletons)
    - State persisted to batch_state.tsv for crash recovery
    """

    def __init__(self, concurrency: int = BATCH_MAX_CONCURRENCY):
        self._concurrency = concurrency
        self._state = BatchState()
        self._worker = BatchWorker()

    async def process_urls(
        self,
        urls: list[str],
        cv_text: str,
        concurrency: Optional[int] = None,
        generate_pdf: bool = True,
    ) -> BatchResult:
        """Process a list of job URLs in parallel.

        Args:
            urls: List of job posting URLs.
            cv_text: Candidate's CV text.
            concurrency: Max parallel workers (default from config).
            generate_pdf: Whether to generate PDFs for high-scoring jobs.

        Returns:
            BatchResult with aggregate statistics.
        """
        max_workers = concurrency or self._concurrency
        start_time = time.monotonic()

        # Load existing state for resumability
        self._state.load()

        # Create batch jobs, skipping already-completed ones
        batch_jobs = []
        for i, url in enumerate(urls, 1):
            existing = self._state.get_by_url(url)
            if existing and existing.status == BatchStatus.COMPLETED:
                print(f"  [batch] Skipping completed: {url}")
                continue
            batch_jobs.append(BatchJob(
                id=existing.id if existing else i,
                url=url,
                status=BatchStatus.PENDING,
            ))

        total = len(batch_jobs)
        print(f"[batch] Processing {total} URLs with {max_workers} workers")
        print(f"[batch] PDF generation: {'enabled' if generate_pdf else 'disabled'}")
        print()

        # Process with semaphore-controlled concurrency
        semaphore = asyncio.Semaphore(max_workers)
        completed = 0
        failed = 0

        async def process_one(job: BatchJob):
            nonlocal completed, failed
            async with semaphore:
                job.status = BatchStatus.PROCESSING
                job.started_at = datetime.utcnow().isoformat()
                self._state.update(job)

                try:
                    result = await self._worker.process(
                        url=job.url,
                        cv_text=cv_text,
                        report_num=job.id,
                        generate_pdf=generate_pdf,
                    )
                    job.status = BatchStatus.COMPLETED
                    job.completed_at = datetime.utcnow().isoformat()
                    job.score = result.get("score")
                    job.report_num = result.get("report_num")
                    completed += 1
                    print(f"  [batch] [OK] [{completed + failed}/{total}] {job.url} -> {job.score}/5.0")

                except Exception as e:
                    job.retries += 1
                    if job.retries < BATCH_MAX_RETRIES:
                        job.status = BatchStatus.PENDING
                        job.error = str(e)
                    else:
                        job.status = BatchStatus.FAILED
                        job.error = str(e)
                        job.completed_at = datetime.utcnow().isoformat()
                        failed += 1
                        print(f"  [batch] [FAIL] [{completed + failed}/{total}] {job.url} -> {e}")

                self._state.update(job)

        # Run all tasks
        tasks = [process_one(job) for job in batch_jobs]
        await asyncio.gather(*tasks)

        elapsed = time.monotonic() - start_time

        result = BatchResult(
            total=total,
            completed=completed,
            failed=failed,
            skipped=len(urls) - total,
            results=self._state.get_all(),
            elapsed_seconds=round(elapsed, 1),
        )

        self._print_summary(result)
        return result

    async def process_file(
        self,
        input_file: Path,
        cv_text: str,
        concurrency: Optional[int] = None,
    ) -> BatchResult:
        """Process URLs from a file (one URL per line)."""
        if not input_file.exists():
            print(f"[batch] File not found: {input_file}")
            return BatchResult()

        urls = [
            line.strip()
            for line in input_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and line.strip().startswith("http")
        ]

        print(f"[batch] Loaded {len(urls)} URLs from {input_file}")
        return await self.process_urls(urls, cv_text, concurrency)

    async def retry_failed(self, cv_text: str) -> BatchResult:
        """Retry all previously failed jobs."""
        self._state.load()
        failed_jobs = self._state.get_failed()

        if not failed_jobs:
            print("[batch] No failed jobs to retry.")
            return BatchResult()

        urls = [j.url for j in failed_jobs]
        # Reset retries
        for j in failed_jobs:
            j.retries = 0
            j.status = BatchStatus.PENDING
            self._state.update(j)

        print(f"[batch] Retrying {len(urls)} failed jobs...")
        return await self.process_urls(urls, cv_text)

    def get_status(self) -> dict:
        """Get current batch processing status."""
        self._state.load()
        all_jobs = self._state.get_all()
        return {
            "total": len(all_jobs),
            "pending": sum(1 for j in all_jobs if j.status == BatchStatus.PENDING),
            "processing": sum(1 for j in all_jobs if j.status == BatchStatus.PROCESSING),
            "completed": sum(1 for j in all_jobs if j.status == BatchStatus.COMPLETED),
            "failed": sum(1 for j in all_jobs if j.status == BatchStatus.FAILED),
            "avg_score": (
                sum(j.score for j in all_jobs if j.score) /
                max(1, sum(1 for j in all_jobs if j.score))
            ),
        }

    def _print_summary(self, result: BatchResult):
        """Print batch processing summary."""
        sep = "=" * 45
        print(f"\n{sep}")
        print("Batch Processing Complete")
        print(sep)
        print(f"Total URLs:            {result.total}")
        print(f"Completed:             {result.completed}")
        print(f"Failed:                {result.failed}")
        print(f"Skipped (already done):{result.skipped}")
        print(f"Time elapsed:          {result.elapsed_seconds:.1f}s")

        if result.completed > 0:
            scores = [j.score for j in result.results if j.score]
            if scores:
                avg = sum(scores) / len(scores)
                print(f"Average score:         {avg:.1f}/5.0")

        print(f"\n-> Run 'python -m agents.cli tracker' to see pipeline status.")
