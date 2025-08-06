"""Tests for ytm_cli.dislikes module"""

import json
import os
from unittest.mock import patch

from ytm_cli.dislikes import DislikeManager


class TestDislikeManagerInit:
    """Tests for DislikeManager initialization"""

    def test_init_default_file(self):
        """Test initialization with default file"""
        with patch("os.path.exists", return_value=False):
            manager = DislikeManager()

            assert manager.dislikes_file == "dislikes.json"
            assert manager._disliked_ids == set()

    def test_init_custom_file(self):
        """Test initialization with custom file"""
        with patch("os.path.exists", return_value=False):
            manager = DislikeManager("custom_dislikes.json")

            assert manager.dislikes_file == "custom_dislikes.json"

    def test_init_loads_existing_dislikes(self, temp_dir, sample_dislikes_data):
        """Test that existing dislikes are loaded on initialization"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        assert "disliked_song_1" in manager._disliked_ids
        assert "disliked_song_2" in manager._disliked_ids
        assert len(manager._disliked_ids) == 2

    def test_init_handles_missing_file(self):
        """Test initialization when dislikes file doesn't exist"""
        with patch("os.path.exists", return_value=False):
            manager = DislikeManager("non_existent.json")

            assert manager._disliked_ids == set()

    def test_init_handles_invalid_json(self, temp_dir):
        """Test initialization with invalid JSON file"""
        dislikes_file = os.path.join(temp_dir, "invalid.json")

        with open(dislikes_file, "w") as f:
            f.write("{ invalid json")

        with patch("builtins.print") as mock_print:
            manager = DislikeManager(dislikes_file)

        assert manager._disliked_ids == set()
        assert any(
            "Warning: Could not load dislikes" in str(call) for call in mock_print.call_args_list
        )

    def test_init_handles_missing_video_ids(self, temp_dir):
        """Test initialization with songs missing videoId"""
        invalid_data = {
            "songs": [
                {"title": "Song without videoId", "artist": "Artist"},
                {"videoId": "valid_id", "title": "Valid Song", "artist": "Artist"},
            ]
        }

        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(invalid_data, f)

        manager = DislikeManager(dislikes_file)

        # Should only load the song with valid videoId
        assert "valid_id" in manager._disliked_ids
        assert len(manager._disliked_ids) == 1


class TestDislikeSong:
    """Tests for dislike_song method"""

    def test_dislike_song_success(self, temp_dir, sample_song):
        """Test successfully disliking a song"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        manager = DislikeManager(dislikes_file)

        with patch("builtins.print") as mock_print:
            result = manager.dislike_song(sample_song)

            assert result is True
            mock_print.assert_called_with("[green]✅ Disliked 'Test Song'[/green]")

            # Verify song was added to disliked set
            assert "test_video_id_123" in manager._disliked_ids

            # Verify file was created with correct data
            assert os.path.exists(dislikes_file)
            with open(dislikes_file, encoding="utf-8") as f:
                data = json.load(f)
                assert len(data["songs"]) == 1
                assert data["songs"][0]["videoId"] == "test_video_id_123"
                assert data["songs"][0]["title"] == "Test Song"

    def test_dislike_song_missing_video_id(self, temp_dir):
        """Test disliking song without videoId"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))
        song_without_id = {"title": "Test Song", "artists": [{"name": "Test Artist"}]}

        with patch("builtins.print") as mock_print:
            result = manager.dislike_song(song_without_id)

            assert result is False
            mock_print.assert_called_with("[red]Cannot dislike song: missing videoId[/red]")

    def test_dislike_song_already_disliked(self, temp_dir, sample_song):
        """Test disliking a song that's already disliked"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        manager = DislikeManager(dislikes_file)

        # Dislike song first time
        manager.dislike_song(sample_song)

        # Try to dislike again
        with patch("builtins.print") as mock_print:
            result = manager.dislike_song(sample_song)

            assert result is False
            mock_print.assert_called_with("[yellow]Song is already disliked[/yellow]")

    def test_dislike_song_file_error(self, temp_dir, sample_song):
        """Test disliking song with file I/O error"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.dislike_song(sample_song)

            assert result is False
            mock_print.assert_called_with("[red]Error disliking song: Permission denied[/red]")

    def test_dislike_song_preserves_existing_dislikes(
        self, temp_dir, sample_song, sample_dislikes_data
    ):
        """Test that disliking a song preserves existing dislikes"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        # Create file with existing dislikes
        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)
        manager.dislike_song(sample_song)

        # Verify all dislikes are preserved
        with open(dislikes_file, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["songs"]) == 3  # 2 existing + 1 new
            video_ids = [song["videoId"] for song in data["songs"]]
            assert "disliked_song_1" in video_ids
            assert "disliked_song_2" in video_ids
            assert "test_video_id_123" in video_ids


class TestIsDisliked:
    """Tests for is_disliked method"""

    def test_is_disliked_true(self, temp_dir, sample_dislikes_data):
        """Test checking if a song is disliked (true case)"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        assert manager.is_disliked("disliked_song_1") is True
        assert manager.is_disliked("disliked_song_2") is True

    def test_is_disliked_false(self, temp_dir):
        """Test checking if a song is disliked (false case)"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        assert manager.is_disliked("not_disliked_song") is False

    def test_is_disliked_empty_string(self, temp_dir):
        """Test checking empty string video ID"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        assert manager.is_disliked("") is False


class TestFilterDislikedSongs:
    """Tests for filter_disliked_songs method"""

    def test_filter_disliked_songs_no_dislikes(self, temp_dir, sample_songs):
        """Test filtering when no songs are disliked"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        result = manager.filter_disliked_songs(sample_songs)

        assert len(result) == len(sample_songs)
        assert result == sample_songs

    def test_filter_disliked_songs_with_dislikes(self, temp_dir, sample_songs):
        """Test filtering with some disliked songs"""
        dislikes_data = {
            "songs": [{"videoId": "song1", "title": "Song One", "artist": "Artist One"}]
        }

        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("builtins.print") as mock_print:
            result = manager.filter_disliked_songs(sample_songs)

        # Should filter out song1
        assert len(result) == 2
        video_ids = [song["videoId"] for song in result]
        assert "song1" not in video_ids
        assert "song2" in video_ids
        assert "song3" in video_ids

        mock_print.assert_called_with("[yellow]Filtered out 1 disliked song(s)[/yellow]")

    def test_filter_disliked_songs_all_disliked(self, temp_dir, sample_songs):
        """Test filtering when all songs are disliked"""
        dislikes_data = {
            "songs": [
                {"videoId": "song1", "title": "Song One"},
                {"videoId": "song2", "title": "Song Two"},
                {"videoId": "song3", "title": "Song Three"},
            ]
        }

        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("builtins.print") as mock_print:
            result = manager.filter_disliked_songs(sample_songs)

        assert len(result) == 0
        mock_print.assert_called_with("[yellow]Filtered out 3 disliked song(s)[/yellow]")

    def test_filter_disliked_songs_missing_video_id(self, temp_dir):
        """Test filtering songs with missing videoId"""
        songs_with_missing_id = [
            {"title": "Song without ID", "artists": [{"name": "Artist"}]},
            {"videoId": "song2", "title": "Song Two", "artists": [{"name": "Artist Two"}]},
        ]

        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        result = manager.filter_disliked_songs(songs_with_missing_id)

        # Songs without videoId should be kept (not filtered)
        assert len(result) == 2


class TestUndislikeSong:
    """Tests for undislike_song method"""

    def test_undislike_song_success(self, temp_dir, sample_dislikes_data):
        """Test successfully undisliking a song"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("builtins.print") as mock_print:
            result = manager.undislike_song("disliked_song_1")

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Removed 'Disliked Song 1' from dislikes[/green]"
            )

            # Verify song was removed from disliked set
            assert "disliked_song_1" not in manager._disliked_ids
            assert "disliked_song_2" in manager._disliked_ids  # Other song should remain

    def test_undislike_song_not_disliked(self, temp_dir):
        """Test undisliking a song that's not disliked"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        with patch("builtins.print") as mock_print:
            result = manager.undislike_song("not_disliked_song")

            assert result is False
            mock_print.assert_called_with("[yellow]Song is not in dislikes[/yellow]")

    def test_undislike_song_file_error(self, temp_dir, sample_dislikes_data):
        """Test undisliking song with file I/O error"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.undislike_song("disliked_song_1")

            assert result is False
            mock_print.assert_called_with(
                "[red]Error removing song from dislikes: Permission denied[/red]"
            )


class TestClearAllDislikes:
    """Tests for clear_all_dislikes method"""

    def test_clear_all_dislikes_success(self, temp_dir, sample_dislikes_data):
        """Test successfully clearing all dislikes"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("builtins.print") as mock_print:
            result = manager.clear_all_dislikes()

            assert result is True
            mock_print.assert_called_with("[green]All dislikes cleared[/green]")

            # Verify file was deleted and set is empty
            assert not os.path.exists(dislikes_file)
            assert len(manager._disliked_ids) == 0

    def test_clear_all_dislikes_no_file(self, temp_dir):
        """Test clearing dislikes when file doesn't exist"""
        manager = DislikeManager(os.path.join(temp_dir, "non_existent.json"))

        with patch("builtins.print") as mock_print:
            result = manager.clear_all_dislikes()

            assert result is True
            mock_print.assert_called_with("[green]All dislikes cleared[/green]")

    def test_clear_all_dislikes_file_error(self, temp_dir, sample_dislikes_data):
        """Test clearing dislikes with file error"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        with patch("os.remove", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.clear_all_dislikes()

            assert result is False
            mock_print.assert_called_with("[red]Error clearing dislikes: Permission denied[/red]")


class TestGetDislikeCount:
    """Tests for get_dislike_count method"""

    def test_get_dislike_count_with_dislikes(self, temp_dir, sample_dislikes_data):
        """Test getting dislike count when dislikes exist"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        with open(dislikes_file, "w", encoding="utf-8") as f:
            json.dump(sample_dislikes_data, f)

        manager = DislikeManager(dislikes_file)

        assert manager.get_dislike_count() == 2

    def test_get_dislike_count_empty(self, temp_dir):
        """Test getting dislike count when no dislikes exist"""
        manager = DislikeManager(os.path.join(temp_dir, "dislikes.json"))

        assert manager.get_dislike_count() == 0


class TestDislikeManagerIntegration:
    """Integration tests for DislikeManager"""

    def test_full_workflow(self, temp_dir, sample_songs):
        """Test complete dislike workflow"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")
        manager = DislikeManager(dislikes_file)

        # Initially no dislikes
        assert manager.get_dislike_count() == 0
        assert not manager.is_disliked("song1")

        # Dislike a song
        song_to_dislike = sample_songs[0]  # song1
        with patch("builtins.print"):
            manager.dislike_song(song_to_dislike)

        # Verify dislike was recorded
        assert manager.get_dislike_count() == 1
        assert manager.is_disliked("song1")

        # Filter songs should remove disliked song
        with patch("builtins.print"):
            filtered = manager.filter_disliked_songs(sample_songs)
        assert len(filtered) == 2
        assert "song1" not in [s["videoId"] for s in filtered]

        # Undislike the song
        with patch("builtins.print"):
            manager.undislike_song("song1")

        # Verify undislike worked
        assert manager.get_dislike_count() == 0
        assert not manager.is_disliked("song1")

        # Filter should now return all songs
        filtered = manager.filter_disliked_songs(sample_songs)
        assert len(filtered) == 3

    def test_persistence_across_instances(self, temp_dir, sample_song):
        """Test that dislikes persist across DislikeManager instances"""
        dislikes_file = os.path.join(temp_dir, "dislikes.json")

        # Create first instance and dislike a song
        manager1 = DislikeManager(dislikes_file)
        with patch("builtins.print"):
            manager1.dislike_song(sample_song)

        # Create second instance and verify dislike persists
        manager2 = DislikeManager(dislikes_file)
        assert manager2.is_disliked("test_video_id_123")
        assert manager2.get_dislike_count() == 1
