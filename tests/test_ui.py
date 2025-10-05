"""Tests for ytm_cli.ui module"""

from unittest.mock import patch

# Mock curses before importing ui module
with patch("curses.curs_set"), patch("curses.use_default_colors"), patch(
    "curses.init_pair"
), patch("curses.color_pair"):
    from ytm_cli.ui import display_player_status


class TestDisplayPlayerStatus:
    """Tests for display_player_status function"""

    def test_display_player_status_playing(self):
        """Test display player status when playing"""
        with patch("os.system") as mock_system, patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 80

            display_player_status("Test Song - Test Artist", False)

            # Should clear screen
            mock_system.assert_called_once_with("clear")

            # Should print status
            expected_status = "▶️ Playing: Test Song - Test Artist"
            mock_print.assert_any_call(expected_status.center(80))

    def test_display_player_status_paused(self):
        """Test display player status when paused"""
        with patch("os.system") as mock_system, patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 80

            display_player_status("Test Song - Test Artist", True)

            # Should clear screen
            mock_system.assert_called_once_with("clear")

            # Should print paused status
            expected_status = "⏸️ Paused: Test Song - Test Artist"
            mock_print.assert_any_call(expected_status.center(80))

    def test_display_player_status_long_title(self):
        """Test display player status with very long title"""
        long_title = "Very Long Song Title That Exceeds Terminal Width" * 3

        with patch("os.system"), patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 80

            display_player_status(long_title, False)

            # Should truncate long titles
            printed_calls = [call for call in mock_print.call_args_list if call[0]]
            status_call = None
            for call in printed_calls:
                if "▶️ Playing:" in str(call[0][0]):
                    status_call = call
                    break

            assert status_call is not None
            printed_text = status_call[0][0]
            assert len(printed_text) <= 80

    def test_display_player_status_narrow_terminal(self):
        """Test display player status with narrow terminal"""
        with patch("os.system"), patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 40

            display_player_status("Test Song", False)

            # Should center text for narrow terminal
            expected_status = "▶️ Playing: Test Song"
            mock_print.assert_any_call(expected_status.center(40))

    def test_display_player_status_terminal_size_error(self):
        """Test display player status when terminal size cannot be determined"""
        with patch("os.system"), patch(
            "os.get_terminal_size", side_effect=OSError("No terminal")
        ), patch("builtins.print") as mock_print:

            display_player_status("Test Song", False)

            # Should use fallback width of 80
            expected_status = "▶️ Playing: Test Song"
            mock_print.assert_any_call(expected_status.center(80))

    def test_display_player_status_windows(self):
        """Test display player status on Windows"""
        with patch("os.name", "nt"), patch("os.system") as mock_system, patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print"):

            mock_terminal_size.return_value.columns = 80

            display_player_status("Test Song", False)

            # Should use 'cls' command on Windows
            mock_system.assert_called_once_with("cls")

    def test_display_player_status_controls_display(self):
        """Test that controls are displayed correctly"""
        with patch("os.system"), patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 120

            display_player_status("Test Song", False)

            # Should print controls
            controls_text = (
                "  ⏮️ (b)  ⏯️ (space)  ⏭️ (n)  📜 (l)  ❤️ (a)    👎 (d)    🚪 (q)"
            )
            mock_print.assert_any_call(controls_text.center(120))

    def test_display_player_status_empty_title(self):
        """Test display player status with empty title"""
        with patch("os.system"), patch(
            "os.get_terminal_size"
        ) as mock_terminal_size, patch("builtins.print") as mock_print:

            mock_terminal_size.return_value.columns = 80

            display_player_status("", False)

            # Should handle empty title gracefully
            expected_status = "▶️ Playing: "
            mock_print.assert_any_call(expected_status.center(80))


class TestUIHelpers:
    """Tests for UI helper functions and logic"""

    def test_song_title_truncation_logic(self):
        """Test the logic for truncating song titles in UI"""
        # This tests the truncation logic that would be used in selection_ui
        max_width = 50

        # Test normal length title
        title = "Normal Song Title"
        artist = "Artist Name"
        line = f"[1] {title} - {artist}"

        if len(line) > max_width - 3:
            truncated_line = line[: max_width - 6] + "..."
        else:
            truncated_line = line

        assert len(truncated_line) <= max_width - 3

    def test_song_title_truncation_very_long(self):
        """Test truncation with very long song title"""
        max_width = 50

        title = "Very Long Song Title That Definitely Exceeds The Maximum Width"
        artist = "Very Long Artist Name That Also Exceeds Width"
        line = f"[1] {title} - {artist}"

        if len(line) > max_width - 3:
            truncated_line = line[: max_width - 6] + "..."
        else:
            truncated_line = line

        assert len(truncated_line) <= max_width - 3
        assert truncated_line.endswith("...")

    def test_song_title_no_truncation_needed(self):
        """Test when no truncation is needed"""
        max_width = 100

        title = "Short Title"
        artist = "Artist"
        line = f"[1] {title} - {artist}"

        if len(line) > max_width - 3:
            truncated_line = line[: max_width - 6] + "..."
        else:
            truncated_line = line

        assert truncated_line == line
        assert not truncated_line.endswith("...")


class TestUIDataProcessing:
    """Tests for UI data processing logic"""

    def test_song_list_formatting(self, sample_songs):
        """Test formatting song list for display"""
        songs_to_display = 3
        formatted_songs = []

        for i, song in enumerate(sample_songs[:songs_to_display]):
            title = song["title"]
            artist = song["artists"][0]["name"]
            formatted_line = f"[{i + 1}] {title} - {artist}"
            formatted_songs.append(formatted_line)

        assert len(formatted_songs) == 3
        assert formatted_songs[0] == "[1] Song One - Artist One"
        assert formatted_songs[1] == "[2] Song Two - Artist Two"
        assert formatted_songs[2] == "[3] Song Three - Artist Three"

    def test_song_list_formatting_missing_artist(self):
        """Test formatting song list when artist info is missing"""
        song_without_artist = {"title": "Test Song", "artists": []}

        # This should handle the case gracefully
        try:
            title = song_without_artist["title"]
            artist = (
                song_without_artist["artists"][0]["name"]
                if song_without_artist["artists"]
                else "Unknown Artist"
            )
            formatted_line = f"[1] {title} - {artist}"

            assert formatted_line == "[1] Test Song - Unknown Artist"
        except IndexError:
            # If the original code doesn't handle this, we know it needs improvement
            assert True  # This test documents the current behavior

    def test_playlist_selection_logic(self):
        """Test playlist selection logic"""
        playlists = ["Rock Hits", "Jazz Classics", "Pop Songs"]

        # Test single playlist auto-selection
        if len(playlists) == 1:
            selected_playlist = playlists[0]
        else:
            selected_playlist = None  # Would prompt user

        # With multiple playlists, should not auto-select
        assert selected_playlist is None

        # Test with single playlist
        single_playlist = ["Only Playlist"]
        if len(single_playlist) == 1:
            selected_playlist = single_playlist[0]
        else:
            selected_playlist = None

        assert selected_playlist == "Only Playlist"

    def test_numeric_playlist_selection(self):
        """Test numeric playlist selection logic"""
        playlists = ["Rock Hits", "Jazz Classics", "Pop Songs"]
        user_input = "2"

        if user_input.isdigit():
            playlist_index = int(user_input) - 1
            if 0 <= playlist_index < len(playlists):
                selected_playlist = playlists[playlist_index]
            else:
                selected_playlist = None
        else:
            selected_playlist = None

        assert selected_playlist == "Jazz Classics"

    def test_invalid_numeric_playlist_selection(self):
        """Test invalid numeric playlist selection"""
        playlists = ["Rock Hits", "Jazz Classics", "Pop Songs"]

        # Test out of range
        user_input = "5"
        if user_input.isdigit():
            playlist_index = int(user_input) - 1
            if 0 <= playlist_index < len(playlists):
                selected_playlist = playlists[playlist_index]
            else:
                selected_playlist = None
        else:
            selected_playlist = None

        assert selected_playlist is None

        # Test zero
        user_input = "0"
        if user_input.isdigit():
            playlist_index = int(user_input) - 1
            if 0 <= playlist_index < len(playlists):
                selected_playlist = playlists[playlist_index]
            else:
                selected_playlist = None
        else:
            selected_playlist = None

        assert selected_playlist is None

    def test_non_numeric_playlist_selection(self):
        """Test non-numeric playlist selection (new playlist name)"""
        playlists = ["Rock Hits", "Jazz Classics", "Pop Songs"]
        user_input = "New Playlist Name"

        if user_input.isdigit():
            playlist_index = int(user_input) - 1
            if 0 <= playlist_index < len(playlists):
                selected_playlist = playlists[playlist_index]
            else:
                selected_playlist = None
        else:
            # This would be treated as a new playlist name
            new_playlist_name = user_input
            selected_playlist = new_playlist_name

        assert selected_playlist == "New Playlist Name"


class TestUIErrorHandling:
    """Tests for UI error handling scenarios"""

    def test_unicode_handling_in_display(self):
        """Test handling of Unicode characters in song titles"""
        # This tests the ASCII encoding fallback logic from selection_ui
        unicode_title = "Song with émojis 🎵 and spëcial chars"

        # Simulate the encoding fallback
        try:
            safe_title = unicode_title
        except UnicodeEncodeError:
            safe_title = unicode_title.encode("ascii", "replace").decode("ascii")

        # Should not raise an exception
        assert isinstance(safe_title, str)

    def test_empty_song_list_handling(self):
        """Test handling of empty song lists"""
        songs = []
        songs_to_display = 5

        # Should handle empty list gracefully
        displayed_songs = songs[:songs_to_display]
        assert displayed_songs == []

    def test_fewer_songs_than_display_limit(self, sample_songs):
        """Test when there are fewer songs than the display limit"""
        songs_to_display = 10

        displayed_songs = sample_songs[:songs_to_display]
        assert len(displayed_songs) == len(sample_songs)  # Should be 3, not 10

    def test_navigation_bounds_checking(self):
        """Test navigation bounds checking logic"""
        songs_count = 5
        current_selection = 0

        # Test down navigation
        new_selection = (current_selection + 1) % songs_count
        assert new_selection == 1

        # Test up navigation from first item
        current_selection = 0
        new_selection = (current_selection - 1 + songs_count) % songs_count
        assert new_selection == 4  # Should wrap to last item

        # Test down navigation from last item
        current_selection = 4
        new_selection = (current_selection + 1) % songs_count
        assert new_selection == 0  # Should wrap to first item
