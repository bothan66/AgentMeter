Implement a thread-safe LRU cache with TTL (time-to-live) support in `/app/lru_ttl_cache.py`.

## Class

```python
class LRUCacheWithTTL:
    def __init__(self, capacity: int, default_ttl: float)
```

`capacity` is the maximum number of physical entries (both expired and non-expired) the cache may hold at any time.
`default_ttl` is the default expiry duration (in seconds) for new entries.

## Methods

- `put(key, value, ttl=None)` — Insert or update `key`. Uses `default_ttl` when `ttl` is omitted. The TTL clock starts at insertion/update time. If the key already exists, its value and TTL are updated, and it becomes the most recently used.
- `get(key) -> value | None` — Return the value if `key` exists **and** is not expired; return `None` otherwise. A successful (non-expired) hit counts as a use and updates LRU order. Accessing an expired or non-existent key does not update the LRU order.
- `delete(key) -> bool` — Remove `key` from the cache entirely. Return `True` if the key was present in the cache (regardless of whether it was expired), `False` otherwise.
- `size() -> int` — Count of **non-expired** entries currently in the cache. Expired entries that have not yet been evicted do not count towards this size.
- `clear()` — Remove all entries (both expired and non-expired).

## Eviction policy

When inserting a new key would exceed `capacity`, exactly one entry must be evicted according to the following strict priority:

1. If there is at least one **non-expired** entry in the cache, evict the **least recently used non-expired** entry.
2. If **all** current entries in the cache are **expired**, evict the **oldest** (least recently used) expired entry.

## Thread safety

All methods must be safe for concurrent access from multiple threads without raising exceptions or corrupting internal state.

## Constraints

- Standard library only — do not use third-party caching libraries.
- `time.monotonic()` is the recommended time source.