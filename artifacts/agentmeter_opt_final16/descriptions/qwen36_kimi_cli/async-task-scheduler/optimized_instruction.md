Implement an async priority task scheduler in `/app/scheduler.py`.

## Class

```python
class AsyncTaskScheduler
```

## Methods

- `async def submit(task_fn, priority: int, *args, **kwargs) -> asyncio.Future`

  Schedule a coroutine function for execution. `priority` is an integer where **lower values run first**. Returns an `asyncio.Future` whose result is set to the return value of `task_fn(*args, **kwargs)` when it completes.

  If two submitted tasks share the same priority, they must run in **FIFO** (submission) order.
  
  The scheduler must accept submissions immediately upon instantiation, even if `start` has not yet been called.

- `async def start(num_workers: int) -> None`

  Start `num_workers` worker coroutines that pull tasks from the internal queue and execute them in priority order. **This method must return immediately** after launching the workers, without blocking or waiting for them to finish. Workers must not stop running when a task raises an exception.

- `async def stop() -> None`

  Signal all workers to stop after draining remaining queued tasks. Wait until all workers have exited before returning.

- `async def get_stats() -> dict`

  Return a dict with exactly these keys:
  ```python
  {"completed": int, "pending": int, "failed": int}
  ```
  - `completed`: tasks that finished without exception.
  - `failed`: tasks that raised an exception.
  - `pending`: tasks currently in the queue (not yet picked up by a worker).

## Constraints

- Standard library only — use `asyncio.PriorityQueue` (no third-party task queues).
- Workers must not crash when a task raises an exception; the exception must be stored on the returned Future (i.e., `future.exception()` returns the exception), and `failed` count incremented.
- The scheduler must work correctly when called from within a running `asyncio` event loop.