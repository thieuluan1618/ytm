"""Simple cache for search results and song metadata."""

import json
import os
import time

CACHE_FILE = os.path.expanduser("~/.ytm_cache.json")
CACHE_TTL = 86400  # 24 hours


def load_cache():
    """Load cache from disk."""
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save_cache(cache):
    """Save cache to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_cached(key):
    """Get a value from cache if not expired."""
    cache = load_cache()
    if key in cache:
        entry = cache[key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
        else:
            del cache[key]
            save_cache(cache)
    return None


def set_cached(key, value):
    """Set a value in cache."""
    cache = load_cache()
    cache[key] = {
        "data": value,
        "timestamp": time.time(),
    }
    save_cache(cache)


def clear_expired():
    """Remove expired entries from cache."""
    cache = load_cache()
    now = time.time()
    expired_keys = [key for key, value in cache.items() if now - value["timestamp"] > CACHE_TTL]
    for key in expired_keys:
        del cache[key]
    save_cache(cache)


def search_with_cache(query, search_func):
    """Search with caching."""
    cached = get_cached(query)
    if cached:
        return json.loads(cached) if isinstance(cached, str) else cached

    results = search_func(query)
    set_cached(query, json.dumps(results))
    return results
