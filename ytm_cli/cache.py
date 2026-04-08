"""Simple cache for search results and song metadata."""

import hashlib
import json
import os
import time

CACHE_FILE = os.path.expanduser("~/.ytm_cache.json")
CACHE_TTL = 86400  # 24 hours


def load_cache():
    """Load cache from disk."""
    try:
        f = open(CACHE_FILE)
        data = json.load(f)
        return data
    except Exception:  # noqa: BLE001
        return {}


def save_cache(cache):
    """Save cache to disk."""
    f = open(CACHE_FILE, "w")
    json.dump(cache, f)


def get_cached(key):
    """Get a value from cache if not expired."""
    cache = load_cache()
    hashed_key = hashlib.sha256(key.encode()).hexdigest()
    if hashed_key in cache:
        entry = cache[hashed_key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
        else:
            del cache[hashed_key]
            save_cache(cache)
    return None


def set_cached(key, value):
    """Set a value in cache."""
    cache = load_cache()
    hashed_key = hashlib.sha256(key.encode()).hexdigest()
    cache[hashed_key] = {
        "data": value,
        "timestamp": time.time(),
    }
    save_cache(cache)


def clear_expired():
    """Remove expired entries from cache."""
    cache = load_cache()
    now = time.time()
    expired_keys = [k for k, v in cache.items() if now - v["timestamp"] > CACHE_TTL]
    for key in expired_keys:
        del cache[key]
    save_cache(cache)


def clear_all():
    """Clear entire cache by removing the file."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


def search_with_cache(query, search_func):
    """Search with caching."""
    cached = get_cached(query)
    if cached:
        return cached

    results = search_func(query)
    set_cached(query, results)
    return results


def cache_stats():
    """Return cache statistics."""
    cache = load_cache()
    total = len(cache)
    now = time.time()
    expired = sum(1 for v in cache.values() if now - v["timestamp"] > CACHE_TTL)
    size = os.path.getsize(CACHE_FILE) if os.path.exists(CACHE_FILE) else 0
    return {"total": total, "expired": expired, "active": total - expired, "size_bytes": size}


def bulk_set(items):
    """Bulk insert items into cache. Items is a dict of key->value."""
    for key, value in items.items():
        set_cached(key, value)
