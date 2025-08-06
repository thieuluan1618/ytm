"""Tests for ytm_cli.lyrics_service module"""

from unittest.mock import Mock, patch

import pytest
import requests

from ytm_cli.lyrics_service import (
    LRCParser,
    LyricsService,
    get_song_metadata_from_item,
    get_timestamped_lyrics,
)


class TestLyricsService:
    """Tests for LyricsService class"""

    def test_init_default_base_url(self):
        """Test initialization with default base URL"""
        service = LyricsService()

        assert service.base_url == "https://lrclib.net/api"
        assert service.session is not None

    def test_init_custom_base_url(self):
        """Test initialization with custom base URL"""
        custom_url = "https://custom-lyrics-api.com"
        service = LyricsService(base_url=custom_url)

        assert service.base_url == custom_url

    def test_get_lyrics_success(self, sample_lyrics_response):
        """Test successful lyrics retrieval"""
        service = LyricsService()

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_lyrics_response
            mock_get.return_value = mock_response

            result = service.get_lyrics("Test Song", "Test Artist", "Test Album", 225)

            assert result == sample_lyrics_response
            mock_get.assert_called_once_with(
                f"{service.base_url}/get",
                params={
                    "track_name": "Test Song",
                    "artist_name": "Test Artist",
                    "album_name": "Test Album",
                    "duration": 225,
                },
                timeout=10,
            )

    def test_get_lyrics_without_optional_params(self, sample_lyrics_response):
        """Test lyrics retrieval without optional parameters"""
        service = LyricsService()

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_lyrics_response
            mock_get.return_value = mock_response

            result = service.get_lyrics("Test Song", "Test Artist")

            assert result == sample_lyrics_response
            mock_get.assert_called_once_with(
                f"{service.base_url}/get",
                params={"track_name": "Test Song", "artist_name": "Test Artist"},
                timeout=10,
            )

    def test_get_lyrics_not_found(self):
        """Test lyrics retrieval when song not found"""
        service = LyricsService()

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with patch("builtins.print") as mock_print:
                result = service.get_lyrics("Unknown Song", "Unknown Artist")

            assert result is None
            mock_print.assert_called_with("LRCLIB error: 404")

    def test_get_lyrics_network_error(self):
        """Test lyrics retrieval with network error"""
        service = LyricsService()

        with patch.object(
            service.session, "get", side_effect=requests.RequestException("Network error")
        ):
            with patch("builtins.print") as mock_print:
                result = service.get_lyrics("Test Song", "Test Artist")

            assert result is None
            mock_print.assert_called_with("Error fetching lyrics from LRCLIB: Network error")

    def test_search_lyrics_success(self):
        """Test successful lyrics search"""
        service = LyricsService()
        search_results = [
            {"id": 1, "trackName": "Test Song 1", "artistName": "Artist 1"},
            {"id": 2, "trackName": "Test Song 2", "artistName": "Artist 2"},
        ]

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = search_results
            mock_get.return_value = mock_response

            result = service.search_lyrics("Test Song")

            assert result == search_results
            mock_get.assert_called_once_with(
                f"{service.base_url}/search", params={"track_name": "Test Song"}, timeout=10
            )

    def test_search_lyrics_no_results(self):
        """Test lyrics search with no results"""
        service = LyricsService()

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            result = service.search_lyrics("Unknown Song")

            assert result == []

    def test_search_lyrics_error(self):
        """Test lyrics search with API error"""
        service = LyricsService()

        with patch.object(service.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            with patch("builtins.print") as mock_print:
                result = service.search_lyrics("Test Song")

            assert result == []
            mock_print.assert_called_with("LRCLIB search error: 500")

    def test_search_lyrics_network_error(self):
        """Test lyrics search with network error"""
        service = LyricsService()

        with patch.object(
            service.session, "get", side_effect=requests.RequestException("Network error")
        ):
            with patch("builtins.print") as mock_print:
                result = service.search_lyrics("Test Song")

            assert result == []
            mock_print.assert_called_with("Error searching lyrics from LRCLIB: Network error")


class TestLRCParser:
    """Tests for LRCParser class"""

    def test_parse_lrc_basic(self, sample_lrc_lyrics):
        """Test basic LRC parsing"""
        result = LRCParser.parse_lrc(sample_lrc_lyrics)

        assert len(result) == 4
        assert result[0] == (12.5, "Line one of the song")
        assert result[1] == (17.2, "Line two of the song")
        assert result[2] == (21.1, "Line three of the song")
        assert result[3] == (25.9, "Line four of the song")

    def test_parse_lrc_empty_string(self):
        """Test parsing empty LRC string"""
        result = LRCParser.parse_lrc("")

        assert result == []

    def test_parse_lrc_no_timestamps(self):
        """Test parsing LRC with no valid timestamps"""
        lrc_content = "Just some text\nWithout timestamps\nShould be ignored"

        result = LRCParser.parse_lrc(lrc_content)

        assert result == []

    def test_parse_lrc_mixed_content(self):
        """Test parsing LRC with mixed valid and invalid lines"""
        lrc_content = """[00:12.50]Valid line one
Invalid line without timestamp
[00:17.20]Valid line two
Another invalid line
[00:21.10]Valid line three"""

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 3
        assert result[0] == (12.5, "Valid line one")
        assert result[1] == (17.2, "Valid line two")
        assert result[2] == (21.1, "Valid line three")

    def test_parse_lrc_different_centisecond_formats(self):
        """Test parsing LRC with different centisecond formats"""
        lrc_content = """[00:12.5]Two digit centiseconds
[00:17.50]Two digit centiseconds
[00:21.500]Three digit centiseconds"""

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 3
        assert result[0] == (12.5, "Two digit centiseconds")
        assert result[1] == (17.5, "Two digit centiseconds")
        assert result[2] == (21.5, "Three digit centiseconds")

    def test_parse_lrc_empty_lines(self):
        """Test parsing LRC with empty lines"""
        lrc_content = """[00:12.50]Line one

[00:17.20]Line two


[00:21.10]Line three
"""

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 3
        assert result[0] == (12.5, "Line one")
        assert result[1] == (17.2, "Line two")
        assert result[2] == (21.1, "Line three")

    def test_parse_lrc_sorted_by_timestamp(self):
        """Test that parsed LRC is sorted by timestamp"""
        lrc_content = """[00:25.90]Fourth line
[00:12.50]First line
[00:21.10]Third line
[00:17.20]Second line"""

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 4
        assert result[0] == (12.5, "First line")
        assert result[1] == (17.2, "Second line")
        assert result[2] == (21.1, "Third line")
        assert result[3] == (25.9, "Fourth line")

    def test_parse_lrc_whitespace_handling(self):
        """Test that whitespace is properly handled"""
        lrc_content = """[00:12.50]  Line with leading spaces
[00:17.20]Line with trailing spaces
[00:21.10]   Line with both   """

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 3
        assert result[0] == (12.5, "Line with leading spaces")
        assert result[1] == (17.2, "Line with trailing spaces")
        assert result[2] == (21.1, "Line with both")

    def test_parse_lrc_edge_case_timestamps(self):
        """Test parsing edge case timestamps"""
        lrc_content = """[00:00.00]Start of song
[59:59.99]End of song
[01:23.45]Middle of song"""

        result = LRCParser.parse_lrc(lrc_content)

        assert len(result) == 3
        assert result[0] == (0.0, "Start of song")
        assert result[1] == (83.45, "Middle of song")  # 1*60 + 23.45
        assert result[2] == (3599.99, "End of song")  # 59*60 + 59.99


class TestGetSongMetadataFromItem:
    """Tests for get_song_metadata_from_item function"""

    def test_get_song_metadata_complete_item(self, sample_song):
        """Test extracting metadata from complete song item"""
        track_name, artist_name, album_name, duration = get_song_metadata_from_item(sample_song)

        assert track_name == "Test Song"
        assert artist_name == "Test Artist"
        assert album_name == "Test Album"
        assert duration == 225

    def test_get_song_metadata_missing_album(self, sample_song):
        """Test extracting metadata when album is missing"""
        song_without_album = sample_song.copy()
        del song_without_album["album"]

        track_name, artist_name, album_name, duration = get_song_metadata_from_item(
            song_without_album
        )

        assert track_name == "Test Song"
        assert artist_name == "Test Artist"
        assert album_name is None
        assert duration == 225


class TestGetTimestampedLyrics:
    """Tests for get_timestamped_lyrics function"""

    def test_get_timestamped_lyrics_success(self, sample_song, sample_lyrics_response):
        """Test successful timestamped lyrics retrieval"""
        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = sample_lyrics_response

            result = get_timestamped_lyrics(sample_song)

            assert result is not None
            assert result["synced_lyrics"] == sample_lyrics_response["syncedLyrics"]
            assert result["plain_lyrics"] == sample_lyrics_response["plainLyrics"]
            assert result["source"] == "LRCLIB"
            assert len(result["parsed_lyrics"]) > 0

    def test_get_timestamped_lyrics_fallback_to_search(self, sample_song):
        """Test fallback to search when exact match fails"""
        search_results = [
            {
                "id": 123,
                "trackName": "Test Song",
                "artistName": "Test Artist",
                "syncedLyrics": "[00:12.50]Search result lyrics",
                "plainLyrics": "Search result lyrics",
            }
        ]

        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = None  # Exact match fails
            mock_service.search_lyrics.return_value = search_results

            result = get_timestamped_lyrics(sample_song)

            assert result is not None
            assert result["synced_lyrics"] == "[00:12.50]Search result lyrics"
            assert result["plain_lyrics"] == "Search result lyrics"
            assert result["source"] == "LRCLIB"

    def test_get_timestamped_lyrics_no_results(self, sample_song):
        """Test when no lyrics are found"""
        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = None
            mock_service.search_lyrics.return_value = []

            result = get_timestamped_lyrics(sample_song)

            assert result is None

    def test_get_timestamped_lyrics_missing_metadata(self):
        """Test with song missing required metadata"""
        incomplete_song = {"videoId": "test_id"}  # Missing title and artists

        result = get_timestamped_lyrics(incomplete_song)

        assert result is None

    def test_get_timestamped_lyrics_no_synced_lyrics(self, sample_song):
        """Test with lyrics response that has no synced lyrics"""
        lyrics_response = {
            "id": 123,
            "trackName": "Test Song",
            "artistName": "Test Artist",
            "plainLyrics": "Just plain lyrics without timestamps",
            "syncedLyrics": None,
        }

        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = lyrics_response

            result = get_timestamped_lyrics(sample_song)

            assert result is not None
            assert result["synced_lyrics"] == ""
            assert result["plain_lyrics"] == "Just plain lyrics without timestamps"
            assert result["parsed_lyrics"] == []  # No synced lyrics to parse

    def test_get_timestamped_lyrics_with_lrc_parsing(self, sample_song):
        """Test that LRC lyrics are properly parsed"""
        lyrics_response = {
            "id": 123,
            "trackName": "Test Song",
            "artistName": "Test Artist",
            "plainLyrics": "Line one\nLine two",
            "syncedLyrics": "[00:12.50]Line one\n[00:17.20]Line two",
        }

        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = lyrics_response

            result = get_timestamped_lyrics(sample_song)

            assert result is not None
            assert len(result["parsed_lyrics"]) == 2
            assert result["parsed_lyrics"][0] == (12.5, "Line one")
            assert result["parsed_lyrics"][1] == (17.2, "Line two")


class TestLyricsServiceIntegration:
    """Integration tests for lyrics service functionality"""

    def test_full_lyrics_workflow(self, sample_song):
        """Test complete lyrics retrieval workflow"""
        # Mock the entire workflow
        lyrics_response = {
            "id": 123,
            "trackName": "Test Song",
            "artistName": "Test Artist",
            "albumName": "Test Album",
            "duration": 225,
            "plainLyrics": "Line one\nLine two\nLine three",
            "syncedLyrics": "[00:12.50]Line one\n[00:17.20]Line two\n[00:21.10]Line three",
        }

        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_lyrics.return_value = lyrics_response

            # Test the complete workflow
            result = get_timestamped_lyrics(sample_song)

            # Verify service was called correctly
            mock_service.get_lyrics.assert_called_once_with(
                "Test Song", "Test Artist", "Test Album", 225
            )

            # Verify result structure
            assert result is not None
            assert "synced_lyrics" in result
            assert "plain_lyrics" in result
            assert "parsed_lyrics" in result
            assert "source" in result

            # Verify parsed lyrics
            assert len(result["parsed_lyrics"]) == 3
            assert all(
                isinstance(item, tuple) and len(item) == 2 for item in result["parsed_lyrics"]
            )
            assert all(
                isinstance(item[0], float) and isinstance(item[1], str)
                for item in result["parsed_lyrics"]
            )

    def test_error_handling_in_workflow(self, sample_song):
        """Test error handling throughout the lyrics workflow"""
        with patch("ytm_cli.lyrics_service.LyricsService") as mock_service_class:
            # Test service initialization error
            mock_service_class.side_effect = Exception("Service init failed")

            result = get_timestamped_lyrics(sample_song)

            # Should handle the error gracefully
            assert result is None

    @pytest.mark.network
    def test_real_api_call(self):
        """Test with real API call (marked as network test)"""
        # This test would make a real API call - only run when network tests are enabled
        service = LyricsService()

        # Use a well-known song for testing
        result = service.search_lyrics("Bohemian Rhapsody")

        # Just verify the API is reachable and returns expected structure
        assert isinstance(result, list)
        if result:  # If results found
            assert "trackName" in result[0]
            assert "artistName" in result[0]

        assert track_name == "Test Song"
        assert artist_name == "Test Artist"
        assert album_name == "Test Album"
        assert duration is None

    def test_get_song_metadata_missing_title(self, sample_song):
        """Test extracting metadata when title is missing"""
        song_without_title = sample_song.copy()
        del song_without_title["title"]

        track_name, artist_name, album_name, duration = get_song_metadata_from_item(
            song_without_title
        )

        assert track_name is None
        assert artist_name == "Test Artist"
        assert album_name == "Test Album"
        assert duration == 225

    def test_get_song_metadata_empty_artists(self, sample_song):
        """Test extracting metadata when artists list is empty"""
        song_empty_artists = sample_song.copy()
        song_empty_artists["artists"] = []

        track_name, artist_name, album_name, duration = get_song_metadata_from_item(
            song_empty_artists
        )

        assert track_name == "Test Song"
        assert artist_name is None
        assert album_name == "Test Album"
        assert duration == 225

    def test_get_song_metadata_missing_artists(self, sample_song):
        """Test extracting metadata when artists key is missing"""
        song_no_artists = sample_song.copy()
        del song_no_artists["artists"]

        track_name, artist_name, album_name, duration = get_song_metadata_from_item(song_no_artists)

        assert track_name == "Test Song"
        assert artist_name is None
        assert album_name == "Test Album"
        assert duration == 225
