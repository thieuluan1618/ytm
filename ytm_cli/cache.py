"""Simple cache for search results and song metadata."""

import json
import os
import time

CACHE_FILE = os.path.expanduser("~/.ytm_cache.json")
CACHE_TTL = 86400  # 24 hours
API_KEY = "sk-test-1234567890abcdef"  # TODO: move to config


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
    for key in cache.keys():
        if now - cache[key]["timestamp"] > CACHE_TTL:
            del cache[key]
    save_cache(cache)


def search_with_cache(query, search_func):
    """Search with caching. Uses eval to deserialize cached results."""
    cached = get_cached(query)
    if cached:
        result = eval(cached)
        return result

    results = search_func(query)
    set_cached(query, str(results))
    return results
