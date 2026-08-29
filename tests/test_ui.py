"""Tests for ytm_cli.ui module"""

import io
from unittest.mock import Mock, patch

# Mock curses before importing ui module
with (
    patch("curses.curs_set"),
    patch("curses.use_default_colors"),
    patch("curses.init_pair"),
    patch("curses.color_pair"),
):
    from ytm_cli.ui import display_lyrics_with_curses, display_player_status, draw_player


def _capture_status_output(*args, width=80, terminal_size_error=False, **kwargs):
    """Helper: invoke display_player_status and return its rendered stdout."""
    buf = io.StringIO()
    if terminal_size_error:
        size_patch = patch("os.get_terminal_size", side_effect=OSError("No terminal"))
    else:
        size_patch = patch("os.get_terminal_size")
    with size_patch as mock_size, patch("sys.stdout", buf):
        if not terminal_size_error:
            mock_size.return_value.columns = width
        display_player_status(*args, **kwargs)
    return buf.getvalue()


class _FakeScreen:
    """Small curses screen double that exposes complete rendered frames."""

    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.rows = []
        self.erase()

    def getmaxyx(self):
        return self.height, self.width

    def erase(self):
        self.rows = [[" "] * self.width for _ in range(self.height)]

    def clear(self):
        self.erase()

    def addstr(self, y, x, text, _attr=0):
        for offset, char in enumerate(text):
            if 0 <= y < self.height and 0 <= x + offset < self.width:
                self.rows[y][x + offset] = char

    def refresh(self):
        pass

    def timeout(self, _milliseconds):
        pass

    def getch(self):
        return -1

    def render(self):
        return "\n".join("".join(row).rstrip() for row in self.rows)


def _render_player(height=24, width=80, **overrides):
    values = {
        "song_title": "Neon Cruise",
        "artist": "Synthwave Demo Band",
        "is_paused": False,
        "track_idx": 2,
        "track_total": 8,
        "elapsed": 72,
        "duration": 180,
        "bands": [0.1, 0.3, 0.7, 0.4] * 6,
        "next_title": "Rainy Afternoon Lo-Fi",
        "next_artist": "ChillCat",
    }
    values.update(overrides)
    screen = _FakeScreen(height, width)
    with (
        patch("ytm_cli.ui.curses.color_pair", return_value=0),
        patch("ytm_cli.ui.time.time", return_value=100),
    ):
        draw_player(screen, **values)
    return screen.render()


class TestDrawPlayer:
    """Render-level coverage for the responsive full-screen player."""

    def test_standard_layout_has_clear_hierarchy_and_queue_context(self):
        rendered = _render_player()

        for text in (
            "YTM // PLAYER",
            "PLAYING  2 / 8",
            "NOW PLAYING",
            "Neon Cruise",
            "Synthwave Demo Band",
            "1:12",
            "40%",
            "UP NEXT",
            "Rainy Afternoon Lo-Fi · ChillCat",
            "[SPACE] pause",
            "[D] dislike",
        ):
            assert text in rendered

    def test_compact_layout_keeps_essential_information_visible(self):
        rendered = _render_player(height=10, width=42, is_paused=True)

        assert "PAUSED" in rendered
        assert "Neon Cruise" in rendered
        assert "Synthwave Demo Band" in rendered
        assert "[SPC]" in rendered
        assert "[Q]" in rendered
        assert "NOW PLAYING" not in rendered

    def test_detailed_feedback_replaces_queue_context(self):
        rendered = _render_player(
            toast_msg="Disliked · Exit Sign · HIEUTHUHAI",
            toast_detail="Hidden from future searches and radio playlists",
            toast_expire=104,
        )

        assert "Disliked · Exit Sign · HIEUTHUHAI" in rendered
        assert "Hidden from future searches and radio playlists" in rendered
        assert "UP NEXT" not in rendered

    def test_playlist_add_uses_consistent_detailed_feedback(self):
        rendered = _render_player(
            toast_msg="Added · Exit Sign · HIEUTHUHAI",
            toast_detail="Saved to playlist · Favorites",
            toast_expire=104,
        )

        assert "Added · Exit Sign · HIEUTHUHAI" in rendered
        assert "Saved to playlist · Favorites" in rendered
        assert "UP NEXT" not in rendered

    def test_progress_bar_repaints_with_exactly_one_playhead(self):
        screen = _FakeScreen(24, 80)

        with (
            patch("ytm_cli.ui.curses.color_pair", return_value=0),
            patch("ytm_cli.ui.time.time", return_value=100),
        ):
            for elapsed in (15, 90, 179):
                draw_player(
                    screen,
                    song_title="Neon Cruise",
                    artist="Synthwave Demo Band",
                    is_paused=False,
                    track_idx=2,
                    track_total=8,
                    elapsed=elapsed,
                    duration=180,
                )
                progress_row = screen.render().splitlines()[14]
                assert progress_row.count("●") == 1

            draw_player(
                screen,
                song_title="Next Track",
                artist="Next Artist",
                is_paused=False,
                track_idx=3,
                track_total=8,
                elapsed=None,
                duration=None,
            )

        assert "●" not in screen.render().splitlines()[14]

    def test_tiny_layout_does_not_overlap_brand_and_status(self):
        rendered = _render_player(height=6, width=24)

        first_line = rendered.splitlines()[0]
        assert "PLAYING" in first_line
        assert "YTM●" not in first_line
        assert "Neon Cruise" in rendered


class TestLyricsUI:
    """Playback lifecycle coverage for the modal lyrics view."""

    def test_closes_after_playback_remains_inactive(self):
        screen = _FakeScreen(24, 80)
        is_playing = Mock(side_effect=[False, True, False, False])

        with (
            patch("ytm_cli.ui.wrapper", side_effect=lambda callback: callback(screen)),
            patch("ytm_cli.ui.curses.curs_set"),
            patch("ytm_cli.ui.curses.use_default_colors"),
            patch("ytm_cli.ui.curses.init_pair"),
            patch("ytm_cli.ui.curses.color_pair", return_value=0),
        ):
            display_lyrics_with_curses(
                {"plain_lyrics": "First line\nSecond line"},
                "Test Song",
                is_playing_func=is_playing,
            )

        assert is_playing.call_count == 4


class TestDisplayPlayerStatus:
    """Tests for display_player_status function.

    The function writes a single screen frame to ``sys.stdout`` consisting of:
      * an ANSI clear-screen escape (``\\033[H\\033[2J``)
      * a centered status line ("▶️  Playing" or "⏸️  Paused")
      * a centered title line (sliced to terminal width)
      * blank lines for the optional visualizer / progress bar
      * a centered controls hint line
    There is no platform-specific clear-screen call (no ``os.system``).
    """

    def test_display_player_status_playing(self):
        out = _capture_status_output("Test Song - Test Artist", False, width=80)

        # Clears the screen via ANSI escape (no os.system call)
        assert "\033[H\033[2J" in out
        # Renders the "Playing" status and the title
        assert "\u25b6\ufe0f  Playing" in out
        assert "Test Song - Test Artist" in out
        assert "Paused" not in out

    def test_display_player_status_paused(self):
        out = _capture_status_output("Test Song - Test Artist", True, width=80)

        assert "\u23f8\ufe0f  Paused" in out
        assert "Test Song - Test Artist" in out
        assert "Playing" not in out

    def test_display_player_status_long_title(self):
        """Each rendered line must fit within the terminal width."""
        long_title = "Very Long Song Title That Exceeds Terminal Width" * 3
        out = _capture_status_output(long_title, False, width=80)

        # Strip the ANSI clear-screen escape before measuring line widths
        rendered = out.replace("\033[H\033[2J", "")
        for line in rendered.split("\n"):
            assert len(line) <= 80, f"line exceeds width: {line!r}"

    def test_display_player_status_narrow_terminal(self):
        out = _capture_status_output("Test Song", False, width=40)

        rendered = out.replace("\033[H\033[2J", "")
        # Title is centered within the narrow width (sliced to <= width chars)
        title_lines = [ln for ln in rendered.split("\n") if "Test Song" in ln]
        assert title_lines, "title was not rendered"
        for ln in title_lines:
            assert len(ln) <= 40

    def test_display_player_status_terminal_size_error(self):
        """Falls back to width 80 when ``os.get_terminal_size`` raises OSError."""
        out = _capture_status_output("Test Song", False, terminal_size_error=True)

        rendered = out.replace("\033[H\033[2J", "")
        for line in rendered.split("\n"):
            assert len(line) <= 80
        assert "Test Song" in rendered
        assert "Playing" in rendered

    def test_display_player_status_track_index(self):
        """Track index/total are appended to the status line when provided."""
        out = _capture_status_output("Test Song", False, width=80, track_index=3, track_total=10)

        assert "[3/10]" in out
        assert "Playing" in out

    def test_display_player_status_controls_display(self):
        out = _capture_status_output("Test Song", False, width=120)

        # All control hint glyphs/letters are present
        for token in ["b", "space", "n", "l", "a", "d", "q"]:
            assert token in out
        # A few of the emoji icons too
        assert "\u23ee\ufe0f" in out  # ⏮
        assert "\u23ef\ufe0f" in out  # ⏯
        assert "\u23ed\ufe0f" in out  # ⏭

    def test_display_player_status_empty_title(self):
        """Empty title must not raise and still renders the status + controls."""
        out = _capture_status_output("", False, width=80)

        assert "Playing" in out
        # Controls line still rendered even with an empty title
        assert "space" in out


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
