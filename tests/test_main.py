"""Tests for ytm_cli.main module"""

from unittest.mock import patch

import pytest

# Mock the imports before importing main to avoid initialization issues
with (
    patch("ytm_cli.main.get_songs_to_display"),
    patch("ytm_cli.main.get_ytmusic"),
    patch("ytm_cli.main.dislike_manager"),
    patch("ytm_cli.main.playlist_manager"),
    patch("ytm_cli.main.setup_signal_handler"),
):
    from ytm_cli.main import (
        main,
        playlist_create_command,
        playlist_delete_command,
        playlist_list_command,
        playlist_play_command,
        playlist_show_command,
        search_and_play,
    )


class TestSearchAndPlay:
    """Tests for search_and_play function"""

    def test_search_and_play_with_query(self, sample_songs):
        """Test search and play with provided query"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.get_songs_to_display", return_value=5),
            patch("ytm_cli.main.wrapper", return_value=0),
            patch("ytm_cli.main.play_music_with_controls"),
            patch("ytm_cli.main.print") as mock_print,
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = sample_songs
            mock_dislike_manager.filter_disliked_songs.return_value = sample_songs
            mock_ytmusic.get_watch_playlist.return_value = {"tracks": []}

            search_and_play("test query")

            mock_ytmusic.search.assert_called_once_with("test query", filter="songs")
            mock_print.assert_any_call("🎵 Searching for: test query")

    def test_search_and_play_no_query_prompts_input(self, sample_songs):
        """Test search and play without query prompts for input"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.get_songs_to_display", return_value=5),
            patch("ytm_cli.main.wrapper", return_value=0),
            patch("ytm_cli.main.play_music_with_controls"),
            patch("builtins.input", return_value="user input query"),
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = sample_songs
            mock_dislike_manager.filter_disliked_songs.return_value = sample_songs
            mock_ytmusic.get_watch_playlist.return_value = {"tracks": []}

            search_and_play()

            mock_ytmusic.search.assert_called_once_with("user input query", filter="songs")

    def test_search_and_play_no_results(self):
        """Test search and play when no results found"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.print") as mock_print,
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = []

            search_and_play("no results query")

            mock_print.assert_called_with("[red]No songs found.[/red]")

    def test_search_and_play_all_filtered_out(self, sample_songs):
        """Test search and play when all results are filtered out"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.print") as mock_print,
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = sample_songs
            mock_dislike_manager.filter_disliked_songs.return_value = []

            search_and_play("filtered query")

            mock_print.assert_called_with("[red]No songs found after filtering dislikes.[/red]")

    def test_search_and_play_user_quits(self, sample_songs):
        """Test search and play when user quits selection"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.get_songs_to_display", return_value=5),
            patch("ytm_cli.main.wrapper", return_value=None),
            patch("ytm_cli.main.play_music_with_controls") as mock_play,
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = sample_songs
            mock_dislike_manager.filter_disliked_songs.return_value = sample_songs

            search_and_play("test query")

            # Should not call play_music_with_controls if user quits
            mock_play.assert_not_called()

    def test_search_and_play_radio_fetch_error(self, sample_songs):
        """Test search and play when radio fetch fails"""
        with (
            patch("ytm_cli.main.get_ytmusic") as mock_get_ytmusic,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.get_songs_to_display", return_value=5),
            patch("ytm_cli.main.wrapper", return_value=0),
            patch("ytm_cli.main.play_music_with_controls") as mock_play,
            patch("ytm_cli.main.print"),
        ):
            mock_ytmusic = mock_get_ytmusic.return_value
            mock_ytmusic.search.return_value = sample_songs
            mock_dislike_manager.filter_disliked_songs.return_value = sample_songs
            mock_ytmusic.get_watch_playlist.side_effect = Exception("Radio error")

            search_and_play("test query")

            # Should still play the selected song even if radio fails
            mock_play.assert_called_once()


class TestPlaylistCommands:
    """Tests for playlist command functions"""

    def test_playlist_list_command_with_playlists(self):
        """Test playlist list command with existing playlists"""
        sample_playlists = [
            {
                "name": "Rock Hits",
                "song_count": 10,
                "description": "",
                "created_at": "2024-01-01",
            },
            {
                "name": "Jazz Classics",
                "song_count": 5,
                "description": "",
                "created_at": "2024-01-02",
            },
        ]

        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("builtins.print"),
        ):
            mock_playlist_manager.list_playlists.return_value = sample_playlists

            playlist_list_command()

            mock_playlist_manager.list_playlists.assert_called_once()

    def test_playlist_list_command_empty(self):
        """Test playlist list command with no playlists"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("ytm_cli.main.print") as mock_print,
        ):
            mock_playlist_manager.list_playlists.return_value = []

            playlist_list_command()

            mock_print.assert_any_call("[yellow]No playlists found.[/yellow]")

    def test_playlist_create_command_success(self):
        """Test successful playlist creation command"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("builtins.print"),
        ):
            mock_playlist_manager.create_playlist.return_value = True

            playlist_create_command("New Playlist", "A test playlist")

            mock_playlist_manager.create_playlist.assert_called_once_with(
                "New Playlist", "A test playlist"
            )

    def test_playlist_create_command_prompt_for_name(self):
        """Test playlist creation command that prompts for name"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("builtins.input", side_effect=["User Playlist", "User description"]),
        ):
            mock_playlist_manager.create_playlist.return_value = True

            playlist_create_command(None, None)

            mock_playlist_manager.create_playlist.assert_called_once_with(
                "User Playlist", "User description"
            )

    def test_playlist_show_command_success(self, sample_playlist_data):
        """Test successful playlist show command"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("builtins.print"),
        ):
            mock_playlist_manager.get_playlist.return_value = sample_playlist_data

            playlist_show_command("Test Playlist")

            mock_playlist_manager.get_playlist.assert_called_once_with("Test Playlist")

    def test_playlist_show_command_not_found(self):
        """Test playlist show command for non-existent playlist"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("ytm_cli.main.print") as mock_print,
        ):
            mock_playlist_manager.get_playlist.return_value = None

            playlist_show_command("Non-existent")

            mock_print.assert_any_call("[red]Playlist 'Non-existent' not found[/red]")

    def test_playlist_play_command_success(self, sample_playlist_data):
        """Test successful playlist play command"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("ytm_cli.main.dislike_manager") as mock_dislike_manager,
            patch("ytm_cli.main.play_music_with_controls") as mock_play,
        ):
            mock_playlist_manager.get_playlist.return_value = sample_playlist_data
            mock_dislike_manager.filter_disliked_songs.return_value = [
                {
                    "title": s.get("title", "Unknown"),
                    "artists": [{"name": s.get("artist", "Unknown")}],
                    "videoId": s["videoId"],
                    "duration_seconds": s.get("duration", ""),
                    "album": None,
                }
                for s in sample_playlist_data["songs"]
                if s.get("videoId")
            ]

            playlist_play_command("Test Playlist")

            mock_play.assert_called_once()

    def test_playlist_delete_command_success(self):
        """Test successful playlist delete command"""
        with (
            patch("ytm_cli.main.playlist_manager") as mock_playlist_manager,
            patch("builtins.input", return_value="y"),
        ):
            mock_playlist_manager.get_playlist_names.return_value = ["Test Playlist"]
            mock_playlist_manager.delete_playlist.return_value = True

            playlist_delete_command("Test Playlist")

            mock_playlist_manager.delete_playlist.assert_called_once_with("Test Playlist")


class TestMainFunction:
    """Tests for main function and argument parsing"""

    def test_main_backward_compatibility_search(self, sample_songs):
        """Test main function with backward compatibility for direct search"""
        test_args = ["ytm_cli", "test song query"]

        with (
            patch("sys.argv", test_args),
            patch("ytm_cli.main.search_and_play") as mock_search_and_play,
        ):
            main()

            mock_search_and_play.assert_called_once_with("test song query")

    def test_main_search_command(self, sample_songs):
        """Test main function with search command"""
        test_args = ["ytm_cli", "search", "test query"]

        with (
            patch("sys.argv", test_args),
            patch("ytm_cli.main.search_and_play") as mock_search_and_play,
        ):
            main()

            mock_search_and_play.assert_called_once_with("test query", auto_select=None)

    def test_main_playlist_list_command(self):
        """Test main function with playlist list command"""
        test_args = ["ytm_cli", "playlist", "list"]

        with (
            patch("sys.argv", test_args),
            patch("ytm_cli.main.playlist_list_command") as mock_playlist_list,
        ):
            main()

            mock_playlist_list.assert_called_once()

    def test_main_playlist_create_command(self):
        """Test main function with playlist create command"""
        test_args = [
            "ytm_cli",
            "playlist",
            "create",
            "New Playlist",
            "--description",
            "Test desc",
        ]

        with (
            patch("sys.argv", test_args),
            patch("ytm_cli.main.playlist_create_command") as mock_playlist_create,
        ):
            main()

            mock_playlist_create.assert_called_once_with("New Playlist", "Test desc")

    def test_main_no_command_prompts_search(self):
        """Test main function with no command prompts for search"""
        test_args = ["ytm_cli"]

        with (
            patch("sys.argv", test_args),
            patch("ytm_cli.main.search_and_play") as mock_search_and_play,
        ):
            main()

            mock_search_and_play.assert_called_once_with()

    def test_main_invalid_playlist_command(self):
        """Test main function with invalid playlist command exits with error"""
        test_args = ["ytm_cli", "playlist", "invalid"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2


class TestMainIntegration:
    """Integration tests for main module functionality"""

    def test_signal_handler_setup(self):
        """Test that signal handler is set up on main execution"""
        with (
            patch("ytm_cli.main.setup_signal_handler") as mock_setup_signal,
            patch("sys.argv", ["ytm_cli"]),
            patch("ytm_cli.main.search_and_play"),
        ):
            main()

            mock_setup_signal.assert_called_once()

    def test_argument_parser_help(self):
        """Test that argument parser can generate help"""
        test_args = ["ytm_cli", "--help"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Help should exit with code 0
            assert exc_info.value.code == 0
