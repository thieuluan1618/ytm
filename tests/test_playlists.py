"""Tests for ytm_cli.playlists module"""

import json
import os
from unittest.mock import patch

from ytm_cli.playlists import PlaylistManager


class TestPlaylistManagerInit:
    """Tests for PlaylistManager initialization"""

    def test_init_default_directory(self):
        """Test initialization with default directory"""
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            manager = PlaylistManager()

            assert manager.playlists_dir == "playlists"

    def test_init_custom_directory(self):
        """Test initialization with custom directory"""
        with patch("os.path.exists", return_value=True), patch("os.makedirs"):
            manager = PlaylistManager("custom_playlists")

            assert manager.playlists_dir == "custom_playlists"

    def test_ensure_playlists_dir_creates_directory(self):
        """Test that directory is created if it doesn't exist"""
        with patch("os.path.exists", return_value=False), patch(
            "os.makedirs"
        ) as mock_makedirs:
            PlaylistManager("test_dir")

            mock_makedirs.assert_called_once_with("test_dir")

    def test_ensure_playlists_dir_exists(self):
        """Test when directory already exists"""
        with patch("os.path.exists", return_value=True), patch(
            "os.makedirs"
        ) as mock_makedirs:
            PlaylistManager("existing_dir")

            mock_makedirs.assert_not_called()


class TestCreatePlaylist:
    """Tests for create_playlist method"""

    def test_create_playlist_success(self, temp_dir):
        """Test successful playlist creation"""
        manager = PlaylistManager(temp_dir)

        with patch("builtins.print") as mock_print:
            result = manager.create_playlist("Test Playlist", "A test playlist")

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Created playlist: Test Playlist[/green]"
            )

            # Verify file was created
            playlist_path = os.path.join(temp_dir, "Test_Playlist.json")
            assert os.path.exists(playlist_path)

            # Verify file content
            with open(playlist_path, encoding="utf-8") as f:
                data = json.load(f)
                assert data["name"] == "Test Playlist"
                assert data["description"] == "A test playlist"
                assert data["songs"] == []
                assert "created_at" in data
                assert "updated_at" in data

    def test_create_playlist_already_exists(self, temp_dir):
        """Test creating playlist that already exists"""
        manager = PlaylistManager(temp_dir)

        # Create playlist first time
        manager.create_playlist("Existing Playlist")

        # Try to create again
        with patch("builtins.print") as mock_print:
            result = manager.create_playlist("Existing Playlist")

            assert result is False
            mock_print.assert_called_with(
                "[red]Playlist 'Existing Playlist' already exists[/red]"
            )

    def test_create_playlist_file_error(self, temp_dir):
        """Test playlist creation with file error"""
        manager = PlaylistManager(temp_dir)

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.create_playlist("Test Playlist")

            assert result is False
            mock_print.assert_called_with(
                "[red]Error creating playlist: Permission denied[/red]"
            )

    def test_safe_filename_conversion(self, temp_dir):
        """Test that unsafe characters are converted in filenames"""
        manager = PlaylistManager(temp_dir)

        # Test with problematic characters
        manager.create_playlist('Test<>:"/\\|?*Playlist')

        # Should create file with safe name
        safe_path = os.path.join(temp_dir, "Test_________Playlist.json")
        assert os.path.exists(safe_path)

    def test_safe_filename_edge_cases(self):
        """Test edge cases for safe filename conversion"""
        manager = PlaylistManager()

        # Test empty name
        assert manager._safe_filename("") == "unnamed_playlist"

        # Test name with only problematic characters
        assert manager._safe_filename('<>:"/\\|?*') == "_________"

        # Test name with leading/trailing dots and spaces
        assert manager._safe_filename("  . test .  ") == "test"


class TestAddSongToPlaylist:
    """Tests for add_song_to_playlist method"""

    def test_add_song_success(self, temp_dir, sample_song):
        """Test successfully adding a song to playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("builtins.print") as mock_print:
            result = manager.add_song_to_playlist("Test Playlist", sample_song)

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Added 'Test Song' to 'Test Playlist'[/green]"
            )

    def test_add_song_playlist_not_found(self, temp_dir, sample_song):
        """Test adding song to non-existent playlist"""
        manager = PlaylistManager(temp_dir)

        with patch("builtins.print") as mock_print:
            result = manager.add_song_to_playlist("Non-existent", sample_song)

            assert result is False
            mock_print.assert_called_with(
                "[red]Playlist 'Non-existent' not found[/red]"
            )

    def test_add_song_duplicate(self, temp_dir, sample_song):
        """Test adding duplicate song to playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        # Add song first time
        manager.add_song_to_playlist("Test Playlist", sample_song)

        # Try to add same song again
        with patch("builtins.print") as mock_print:
            result = manager.add_song_to_playlist("Test Playlist", sample_song)

            assert result is False
            mock_print.assert_called_with(
                "[yellow]Song 'Test Song' is already in the playlist[/yellow]"
            )

    def test_add_song_file_error(self, temp_dir, sample_song):
        """Test adding song with file I/O error"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("builtins.open", side_effect=OSError("Disk full")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.add_song_to_playlist("Test Playlist", sample_song)

            assert result is False
            mock_print.assert_called_with(
                "[red]Error adding song to playlist: Disk full[/red]"
            )

    def test_add_song_updates_timestamp(self, temp_dir, sample_song):
        """Test that adding song updates the playlist timestamp"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        # Get initial timestamp
        playlist_path = os.path.join(temp_dir, "Test_Playlist.json")
        with open(playlist_path, encoding="utf-8") as f:
            initial_data = json.load(f)
            initial_timestamp = initial_data["updated_at"]

        # Add song (with a small delay to ensure timestamp difference)
        import time

        time.sleep(0.01)
        manager.add_song_to_playlist("Test Playlist", sample_song)

        # Check updated timestamp
        with open(playlist_path, encoding="utf-8") as f:
            updated_data = json.load(f)
            updated_timestamp = updated_data["updated_at"]

        assert updated_timestamp > initial_timestamp


class TestListPlaylists:
    """Tests for list_playlists method"""

    def test_list_playlists_empty(self, temp_dir):
        """Test listing playlists when directory is empty"""
        manager = PlaylistManager(temp_dir)

        result = manager.list_playlists()

        assert result == []

    def test_list_playlists_with_playlists(self, temp_dir):
        """Test listing existing playlists"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Playlist 1", "First playlist")
        manager.create_playlist("Playlist 2", "Second playlist")

        result = manager.list_playlists()

        assert len(result) == 2
        playlist_names = [p["name"] for p in result]
        assert "Playlist 1" in playlist_names
        assert "Playlist 2" in playlist_names

    def test_list_playlists_ignores_non_json(self, temp_dir):
        """Test that non-JSON files are ignored"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Valid Playlist")

        # Create a non-JSON file
        with open(os.path.join(temp_dir, "not_a_playlist.txt"), "w") as f:
            f.write("This is not a playlist")

        result = manager.list_playlists()

        assert len(result) == 1
        assert result[0]["name"] == "Valid Playlist"

    def test_list_playlists_handles_invalid_json(self, temp_dir):
        """Test handling of invalid JSON files"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Valid Playlist")

        # Create invalid JSON file
        with open(os.path.join(temp_dir, "invalid.json"), "w") as f:
            f.write("{ invalid json")

        with patch("builtins.print") as mock_print:
            result = manager.list_playlists()

        assert len(result) == 1
        assert result[0]["name"] == "Valid Playlist"
        # Should print warning about invalid JSON
        assert any(
            "Error reading playlist" in str(call) for call in mock_print.call_args_list
        )


class TestGetPlaylist:
    """Tests for get_playlist method"""

    def test_get_playlist_success(self, temp_dir, sample_song):
        """Test successfully getting a playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist", "A test playlist")
        manager.add_song_to_playlist("Test Playlist", sample_song)

        result = manager.get_playlist("Test Playlist")

        assert result is not None
        assert result["name"] == "Test Playlist"
        assert result["description"] == "A test playlist"
        assert len(result["songs"]) == 1
        assert result["songs"][0]["title"] == "Test Song"

    def test_get_playlist_not_found(self, temp_dir):
        """Test getting non-existent playlist"""
        manager = PlaylistManager(temp_dir)

        result = manager.get_playlist("Non-existent")

        assert result is None

    def test_get_playlist_file_error(self, temp_dir):
        """Test getting playlist with file error"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("builtins.open", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.get_playlist("Test Playlist")

            assert result is None
            mock_print.assert_called_with(
                "[red]Error reading playlist: Permission denied[/red]"
            )


class TestDeletePlaylist:
    """Tests for delete_playlist method"""

    def test_delete_playlist_success(self, temp_dir):
        """Test successfully deleting a playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("builtins.print") as mock_print:
            result = manager.delete_playlist("Test Playlist")

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Deleted playlist: Test Playlist[/green]"
            )

            # Verify file was deleted
            playlist_path = os.path.join(temp_dir, "Test_Playlist.json")
            assert not os.path.exists(playlist_path)

    def test_delete_playlist_not_found(self, temp_dir):
        """Test deleting non-existent playlist"""
        manager = PlaylistManager(temp_dir)

        with patch("builtins.print") as mock_print:
            result = manager.delete_playlist("Non-existent")

            assert result is False
            mock_print.assert_called_with(
                "[red]Playlist 'Non-existent' not found[/red]"
            )

    def test_delete_playlist_file_error(self, temp_dir):
        """Test deleting playlist with file error"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("os.remove", side_effect=OSError("Permission denied")), patch(
            "builtins.print"
        ) as mock_print:
            result = manager.delete_playlist("Test Playlist")

            assert result is False
            mock_print.assert_called_with(
                "[red]Error deleting playlist: Permission denied[/red]"
            )


class TestRemoveSongFromPlaylist:
    """Tests for remove_song_from_playlist method"""

    def test_remove_song_success(self, temp_dir, sample_song):
        """Test successfully removing a song from playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")
        manager.add_song_to_playlist("Test Playlist", sample_song)

        with patch("builtins.print") as mock_print:
            result = manager.remove_song_from_playlist(
                "Test Playlist", "test_video_id_123"
            )

            assert result is True
            mock_print.assert_called_with(
                "[green]✅ Removed 'Test Song' from 'Test Playlist'[/green]"
            )

    def test_remove_song_playlist_not_found(self, temp_dir):
        """Test removing song from non-existent playlist"""
        manager = PlaylistManager(temp_dir)

        with patch("builtins.print") as mock_print:
            result = manager.remove_song_from_playlist("Non-existent", "video_id")

            assert result is False
            mock_print.assert_called_with(
                "[red]Playlist 'Non-existent' not found[/red]"
            )

    def test_remove_song_not_in_playlist(self, temp_dir):
        """Test removing song that's not in playlist"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Test Playlist")

        with patch("builtins.print") as mock_print:
            result = manager.remove_song_from_playlist(
                "Test Playlist", "non_existent_id"
            )

            assert result is False
            mock_print.assert_called_with("[yellow]Song not found in playlist[/yellow]")


class TestGetPlaylistNames:
    """Tests for get_playlist_names method"""

    def test_get_playlist_names(self, temp_dir):
        """Test getting list of playlist names"""
        manager = PlaylistManager(temp_dir)
        manager.create_playlist("Rock Hits")
        manager.create_playlist("Jazz Classics")
        manager.create_playlist("Pop Songs")

        result = manager.get_playlist_names()

        assert len(result) == 3
        assert "Rock Hits" in result
        assert "Jazz Classics" in result
        assert "Pop Songs" in result

    def test_get_playlist_names_empty(self, temp_dir):
        """Test getting playlist names when no playlists exist"""
        manager = PlaylistManager(temp_dir)

        result = manager.get_playlist_names()

        assert result == []
