#!/bin/bash
# Solution for async-task-scheduler
# Creates /app/scheduler.py with a complete AsyncTaskScheduler implementation.

set -e

cat > /app/scheduler.py << 'PYEOF'
"""Async priority task scheduler backed by asyncio.PriorityQueue."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine


class AsyncTaskScheduler:
    """Priority-based async task scheduler.

    Lower priority values are executed first.
    Equal-priority tasks are executed in FIFO (submission) order.
    Workers survive individual task failures.
    """

    def __init__(self) -> None:
        # Each item: (priority, sequence, task_fn, args, kwargs, future)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._seq: int = 0
        self._completed: int = 0
        self._failed: int = 0
        self._workers: list[asyncio.Task] = []
        self._stop_event: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def submit(
        self,
        task_fn: Callable[..., Coroutine],
        priority: int,
        *args: Any,
        **kwargs: Any,
    ) -> asyncio.Future:
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        async with self._lock:
            seq = self._seq
            self._seq += 1
        await self._queue.put((priority, seq, task_fn, args, kwargs, future))
        return future

    async def start(self, num_workers: int) -> None:
        self._stop_event.clear()
        for _ in range(num_workers):
            worker_task = asyncio.ensure_future(self._worker())
            self._workers.append(worker_task)

    async def stop(self) -> None:
        # Signal workers to stop after the queue is drained
        self._stop_event.set()
        # Wait for all workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def get_stats(self) -> dict:
        return {
            "completed": self._completed,
            "pending": self._queue.qsize(),
            "failed": self._failed,
        }

    # ------------------------------------------------------------------
    # worker
    # ------------------------------------------------------------------

    async def _worker(self) -> None:
        while True:
            # Try to get a task; if stop is set and queue is empty, exit
            if self._stop_event.is_set() and self._queue.empty():
                return
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                if self._stop_event.is_set():
                    return
                # Yield and retry
                await asyncio.sleep(0)
                continue

            priority, seq, task_fn, args, kwargs, future = item
            try:
                result = await task_fn(*args, **kwargs)
                if not future.done():
                    future.set_result(result)
                async with self._lock:
                    self._completed += 1
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
                async with self._lock:
                    self._failed += 1
            finally:
                self._queue.task_done()
PYEOF

echo "Solution written to /app/scheduler.py"
