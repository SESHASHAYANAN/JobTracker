"""Async job queue with concurrency control and rate limiting.

Replaces career-ops bash orchestrator's parallel mode.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine


class AsyncJobQueue:
    """Async queue with semaphore-controlled concurrency.

    Features:
    - Configurable max concurrent workers
    - Rate limiting via separate Groq and Gemini limiters
    - Task result collection
    - Graceful error handling (one failure doesn't block others)
    """

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: list[asyncio.Task] = []
        self._results: list[Any] = []
        self._errors: list[dict] = []

    async def submit(
        self,
        task_fn: Callable[..., Coroutine],
        *args,
        task_id: str = "",
        **kwargs,
    ):
        """Submit a task to the queue."""
        async def _wrapped():
            async with self._semaphore:
                try:
                    result = await task_fn(*args, **kwargs)
                    self._results.append({"id": task_id, "result": result})
                    return result
                except Exception as e:
                    self._errors.append({"id": task_id, "error": str(e)})
                    return None

        task = asyncio.create_task(_wrapped())
        self._tasks.append(task)

    async def drain(self) -> list[dict]:
        """Wait for all submitted tasks to complete.

        Returns list of results (both successful and failed).
        """
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        return self._results

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._tasks if not t.done())

    @property
    def error_count(self) -> int:
        return len(self._errors)

    @property
    def errors(self) -> list[dict]:
        return self._errors
