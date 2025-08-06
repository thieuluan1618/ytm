"""Pytest configuration and fixtures for YTM CLI tests"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config_file(temp_dir):
    """Create a mock config.ini file"""
    config_content = """[general]
songs_to_display = 5
show_thumbnails = true

[mpv]
flags = --no-video

[playlists]
directory = playlists
"""
    config_path = os.path.join(temp_dir, "config.ini")
    with open(config_path, "w") as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def sample_song():
    """Sample song data for testing"""
    return {
        "videoId": "test_video_id_123",
        "title": "Test Song",
        "artists": [{"name": "Test Artist"}],
        "album": {"name": "Test Album"},
        "duration": "3:45",
        "duration_seconds": 225,
        "thumbnails": [{"url": "http://example.com/thumb.jpg"}]
    }


@pytest.fixture
def sample_songs():
    """Multiple sample songs for testing"""
    return [
        {
            "videoId": "song1",
            "title": "Song One",
            "artists": [{"name": "Artist One"}],
            "album": {"name": "Album One"},
            "duration": "3:30"
        },
        {
            "videoId": "song2", 
            "title": "Song Two",
            "artists": [{"name": "Artist Two"}],
            "album": {"name": "Album Two"},
            "duration": "4:15"
        },
        {
            "videoId": "song3",
            "title": "Song Three", 
            "artists": [{"name": "Artist Three"}],
            "album": {"name": "Album Three"},
            "duration": "2:45"
        }
    ]


@pytest.fixture
def sample_playlist_data():
    """Sample playlist data for testing"""
    return {
        "name": "Test Playlist",
        "description": "A test playlist",
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
        "songs": [
            {
                "videoId": "song1",
                "title": "Song One",
                "artist": "Artist One",
                "added_at": "2024-01-01T12:00:00"
            }
        ]
    }


@pytest.fixture
def sample_dislikes_data():
    """Sample dislikes data for testing"""
    return {
        "songs": [
            {
                "videoId": "disliked_song_1",
                "title": "Disliked Song 1",
                "artist": "Artist 1",
                "disliked_at": "2024-01-01T12:00:00"
            },
            {
                "videoId": "disliked_song_2", 
                "title": "Disliked Song 2",
                "artist": "Artist 2",
                "disliked_at": "2024-01-01T13:00:00"
            }
        ]
    }


@pytest.fixture
def mock_ytmusic():
    """Mock YTMusic instance"""
    mock = Mock()
    mock.search.return_value = []
    mock.get_watch_playlist.return_value = {"tracks": []}
    return mock


@pytest.fixture
def mock_requests_session():
    """Mock requests session for API calls"""
    mock = Mock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = {}
    return mock


@pytest.fixture
def sample_lrc_lyrics():
    """Sample LRC format lyrics for testing"""
    return """[00:12.50]Line one of the song
[00:17.20]Line two of the song
[00:21.10]Line three of the song
[00:25.90]Line four of the song"""


@pytest.fixture
def sample_lyrics_response():
    """Sample lyrics API response"""
    return {
        "id": 123,
        "trackName": "Test Song",
        "artistName": "Test Artist",
        "albumName": "Test Album",
        "duration": 225,
        "plainLyrics": "Line one\nLine two\nLine three\nLine four",
        "syncedLyrics": "[00:12.50]Line one of the song\n[00:17.20]Line two of the song"
    }


@pytest.fixture(autouse=True)
def mock_signal_handler():
    """Mock signal handler to prevent interference during tests"""
    with patch('ytm_cli.utils.setup_signal_handler'):
        yield


@pytest.fixture
def mock_mpv_process():
    """Mock MPV process for player tests"""
    mock = Mock()
    mock.poll.return_value = None  # Process is running
    mock.terminate.return_value = None
    mock.wait.return_value = 0
    return mock
