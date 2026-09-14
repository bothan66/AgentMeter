#!/bin/bash
# Solution for lru-cache-with-ttl
# Creates /app/lru_ttl_cache.py with a complete thread-safe LRU+TTL implementation.

set -e

cat > /app/lru_ttl_cache.py << 'PYEOF'
"""Thread-safe LRU cache with per-entry TTL support."""

import threading
import time
from collections import OrderedDict


class LRUCacheWithTTL:
    """LRU cache where each entry carries an expiry timestamp.

    Parameters
    ----------
    capacity:    maximum number of entries (expired + valid combined).
    default_ttl: default TTL in seconds used when put() receives no ttl argument.
    """

    def __init__(self, capacity: int, default_ttl: float) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._default_ttl = default_ttl
        # OrderedDict maps key -> (value, expiry_monotonic)
        # LRU order: oldest/LRU = first (left), newest/MRU = last (right)
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def put(self, key, value, ttl=None) -> None:
        """Insert or update key. Evicts LRU entry if over capacity."""
        expiry = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            if key in self._cache:
                # Move to MRU position
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry)
            # Evict until we are within capacity
            while len(self._cache) > self._capacity:
                self._evict_one()

    def get(self, key):
        """Return value if present and not expired, else None."""
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                return None
            # Touch — move to MRU position
            self._cache.move_to_end(key)
            return value

    def delete(self, key) -> bool:
        """Remove key. Returns True if it existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def size(self) -> int:
        """Count of non-expired entries."""
        now = time.monotonic()
        with self._lock:
            return sum(1 for _v, exp in self._cache.values() if exp > now)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------
    # private helpers (must be called under self._lock)
    # ------------------------------------------------------------------

    def _evict_one(self) -> None:
        """Evict the LRU non-expired entry; if all expired, evict LRU expired."""
        now = time.monotonic()
        # Iterate from LRU (first) toward MRU (last)
        for key, (_v, expiry) in self._cache.items():
            if expiry > now:          # non-expired → evict it (it's the LRU live one)
                del self._cache[key]
                return
        # All expired → pop the oldest (LRU = first)
        self._cache.popitem(last=False)
PYEOF

echo "Solution written to /app/lru_ttl_cache.py"
