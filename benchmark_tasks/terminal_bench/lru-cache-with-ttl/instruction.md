Implement a thread-safe LRU cache with TTL (time-to-live) support in `/app/lru_ttl_cache.py`.

## Class

```python
class LRUCacheWithTTL(capacity: int, default_ttl: float)
```

`capacity` is the maximum number of entries the cache may hold at any time.
`default_ttl` is the default expiry duration (in seconds) for new entries.

## Methods

- `put(key, value, ttl=None)` — Insert or update `key`. Uses `default_ttl` when `ttl` is omitted. The TTL clock starts at insertion/update time.
- `get(key) -> value | None` — Return the value if `key` exists **and** is not expired; return `None` otherwise. A successful (non-expired) hit counts as a use and updates LRU order.
- `delete(key) -> bool` — Remove `key`. Return `True` if the key existed, `False` otherwise.
- `size() -> int` — Count of **non-expired** entries currently in the cache.
- `clear()` — Remove all entries.

## Eviction policy

When inserting a new key would exceed `capacity`:

1. Evict the **least recently used non-expired** entry.
2. If **all** current entries are expired, evict the **oldest** (least recently used) expired entry.

## Thread safety

All methods must be safe for concurrent access from multiple threads without raising exceptions or corrupting internal state.

## Constraints

- Standard library only — do not use third-party caching libraries.
- `time.monotonic()` is the recommended time source.
