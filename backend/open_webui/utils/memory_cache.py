from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float | None


class MemoryCache:
    """Small async-safe in-process TTL cache.

    This cache is local to the current worker process. It is intended for
    read-through application data where stale values can be invalidated by the
    code path that mutates the source of truth.
    """

    def __init__(self, max_entries: int = 1024, ttl: int | None = 300):
        self.max_entries = max(1, max_entries)
        self.ttl = ttl if ttl and ttl > 0 else None
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    def _expires_at(self) -> float | None:
        return time.monotonic() + self.ttl if self.ttl else None

    @staticmethod
    def _is_expired(entry: _CacheEntry) -> bool:
        return entry.expires_at is not None and entry.expires_at <= time.monotonic()

    async def get(self, key: str) -> T | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None

            if self._is_expired(entry):
                self._entries.pop(key, None)
                return None

            self._entries.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: T) -> None:
        async with self._lock:
            self._entries[key] = _CacheEntry(value=value, expires_at=self._expires_at())
            self._entries.move_to_end(key)

            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)

    async def delete_prefix(self, prefix: str) -> None:
        async with self._lock:
            for key in [key for key in self._entries if key.startswith(prefix)]:
                self._entries.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._entries.clear()
