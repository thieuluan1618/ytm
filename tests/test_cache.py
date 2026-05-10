"""Tests for ytm_cli.cache."""

import json
import time
from unittest.mock import patch

import pytest

from ytm_cli import cache as cache_module


@pytest.fixture
def temp_cache_file(tmp_path, monkeypatch):
    """Redirect CACHE_FILE to an isolated temp path for each test."""
    path = tmp_path / "ytm_cache.json"
    monkeypatch.setattr(cache_module, "CACHE_FILE", str(path))
    return path


class TestLoadSaveCache:
    def test_load_cache_returns_empty_dict_when_missing(self, temp_cache_file):
        assert cache_module.load_cache() == {}

    def test_load_cache_returns_empty_dict_on_invalid_json(self, temp_cache_file):
        temp_cache_file.write_text("not json {{{")
        assert cache_module.load_cache() == {}

    def test_save_cache_then_load_round_trip(self, temp_cache_file):
        payload = {"k": {"data": "v", "timestamp": 1234.0}}
        cache_module.save_cache(payload)
        assert json.loads(temp_cache_file.read_text()) == payload
        assert cache_module.load_cache() == payload


class TestGetSetCached:
    def test_get_cached_missing_key_returns_none(self, temp_cache_file):
        assert cache_module.get_cached("nope") is None

    def test_set_then_get_returns_value(self, temp_cache_file):
        cache_module.set_cached("query1", "result1")
        assert cache_module.get_cached("query1") == "result1"

    def test_get_cached_expired_entry_removed_and_returns_none(self, temp_cache_file):
        # Write an entry with timestamp older than the TTL.
        old_ts = time.time() - cache_module.CACHE_TTL - 100
        cache_module.save_cache({"old": {"data": "stale", "timestamp": old_ts}})

        assert cache_module.get_cached("old") is None
        # Expired entry should be evicted from disk on read.
        assert "old" not in cache_module.load_cache()

    def test_set_cached_overwrites_existing(self, temp_cache_file):
        cache_module.set_cached("k", "v1")
        cache_module.set_cached("k", "v2")
        assert cache_module.get_cached("k") == "v2"


class TestClearExpired:
    def test_clear_expired_removes_only_old_entries(self, temp_cache_file):
        now = time.time()
        cache_module.save_cache(
            {
                "fresh": {"data": "a", "timestamp": now},
                "stale": {"data": "b", "timestamp": now - cache_module.CACHE_TTL - 10},
            }
        )

        cache_module.clear_expired()

        remaining = cache_module.load_cache()
        assert "fresh" in remaining
        assert "stale" not in remaining

    def test_clear_expired_on_empty_cache_is_noop(self, temp_cache_file):
        cache_module.clear_expired()
        assert cache_module.load_cache() == {}


class TestSearchWithCache:
    def test_search_with_cache_calls_search_func_on_miss(self, temp_cache_file):
        search_func = lambda q: [{"title": q}]  # noqa: E731

        result = cache_module.search_with_cache("song", search_func)

        assert result == [{"title": "song"}]
        # Underlying entry is JSON-serialized.
        stored = cache_module.get_cached("song")
        assert json.loads(stored) == [{"title": "song"}]

    def test_search_with_cache_uses_cached_value_on_hit(self, temp_cache_file):
        calls = {"n": 0}

        def search_func(q):
            calls["n"] += 1
            return [{"title": q}]

        cache_module.search_with_cache("song", search_func)
        cache_module.search_with_cache("song", search_func)

        assert calls["n"] == 1  # second call served from cache

    def test_search_with_cache_handles_non_string_cached_value(self, temp_cache_file):
        # Pre-populate cache with a non-string (already-deserialized) value.
        cache_module.set_cached("song", [{"title": "song"}])

        # search_func should NOT be called.
        with patch.object(cache_module, "save_cache") as mock_save:
            result = cache_module.search_with_cache("song", lambda q: pytest.fail("must not call"))

        assert result == [{"title": "song"}]
        mock_save.assert_not_called()
