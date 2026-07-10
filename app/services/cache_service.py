"""
In-memory Cache Service with Time-To-Live (TTL) support.
Thread-safe implementation for caching route descriptions and translation responses.
"""

import time
import threading
from typing import Dict, Any, Tuple, Optional

class CacheService:
    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from the cache. Returns None if key not found or expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiration = self._cache[key]
            if time.time() > expiration:
                # Purge expired item
                del self._cache[key]
                return None
                
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store an item in the cache with a specified Time-To-Live in seconds."""
        with self._lock:
            expiration = time.time() + ttl_seconds
            self._cache[key] = (value, expiration)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current active cache count, pruning expired entries."""
        with self._lock:
            now = time.time()
            # Prune on size check to keep it fresh
            keys_to_delete = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in keys_to_delete:
                del self._cache[k]
            return len(self._cache)

# Global singleton instance
cache_service = CacheService()
