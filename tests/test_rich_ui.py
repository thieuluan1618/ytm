"""Unit tests for rich_ui module."""

from io import StringIO

import pytest
from rich.console import Console

from ytm_cli.rich_ui import (
    CustomProgressBar,
    create_player_layout,
    create_progress_bar,
    play_with_rich_ui,
)


class TestCustomProgressBar:
    """Tests for the custom progress bar component."""

    def test_renders_empty_bar_with_no_duration(self):
        """Empty bar should show all light lines."""
        # Use a Progress instance to create a valid task
        progress = create_progress_bar(elapsed=None, duration=None)
        task = progress.tasks[0]

        bar = CustomProgressBar()
        result = bar.render(task)

        # Should contain only ─ characters (dim)
        assert "─" in str(result)

    def test_renders_progress_at_50_percent(self):
        """Progress bar at 50% should show playhead in middle."""
        # Use a Progress instance to create a valid task
        progress = create_progress_bar(elapsed=90.0, duration=180.0)
        task = progress.tasks[0]

        bar = CustomProgressBar()
        result = bar.render(task)
        rendered = str(result)

        # Should contain filled (━), playhead (●), and empty (─)
        assert "━" in rendered
        assert "●" in rendered
        assert "─" in rendered


class TestCreateProgressBar:
    """Tests for progress bar creation."""

    def test_creates_bar_with_valid_times(self):
        """Progress bar should be created with elapsed and duration."""
        progress = create_progress_bar(elapsed=60.0, duration=180.0)

        assert progress is not None
        assert len(progress.tasks) == 1

        task = progress.tasks[0]
        assert task.total == 180.0
        assert task.completed == 60.0

    def test_creates_bar_with_none_times(self):
        """Progress bar should handle None values gracefully."""
        progress = create_progress_bar(elapsed=None, duration=None)

        assert progress is not None
        assert len(progress.tasks) == 1

    def test_formats_time_correctly(self):
        """Time formatting should show MM:SS."""
        progress = create_progress_bar(elapsed=90.0, duration=180.0)
        task = progress.tasks[0]

        # Check that time_str field is formatted
        assert "1:30" in task.fields["time_str"]
        assert "3:00" in task.fields["time_str"]

    def test_calculates_percentage(self):
        """Percentage should be calculated correctly."""
        progress = create_progress_bar(elapsed=90.0, duration=180.0)
        task = progress.tasks[0]

        assert task.fields["percent"] == "50%"


class TestCreatePlayerLayout:
    """Tests for player layout creation."""

    @staticmethod
    def render(layout):
        output = StringIO()
        console = Console(file=output, width=120, height=20, color_system=None)
        console.print(layout)
        return output.getvalue()

    def test_creates_layout_with_basic_info(self):
        """Layout should contain song info."""
        layout = create_player_layout(
            song_title="Test Song",
            artist="Test Artist",
            is_paused=False,
            track_idx=1,
            track_total=5,
            elapsed=60.0,
            duration=180.0,
        )

        assert layout is not None

    def test_shows_paused_state(self):
        """Layout should reflect paused state."""
        layout = create_player_layout(
            song_title="Test Song",
            artist="Test Artist",
            is_paused=True,
            track_idx=1,
            track_total=5,
            elapsed=60.0,
            duration=180.0,
        )

        rendered = self.render(layout)
        assert "⏸ PAUSED" in rendered
        assert "▶ space" in rendered

    def test_shows_toast_message(self):
        """Layout should display toast notifications."""
        layout = create_player_layout(
            song_title="Test Song",
            artist="Test Artist",
            is_paused=False,
            track_idx=1,
            track_total=5,
            elapsed=60.0,
            duration=180.0,
            toast_msg="Added to playlist",
            toast_detail="Saved to Favorites",
        )

        assert layout is not None

    def test_shows_next_track_info(self):
        """Layout should show upcoming track."""
        layout = create_player_layout(
            song_title="Test Song",
            artist="Test Artist",
            is_paused=False,
            track_idx=1,
            track_total=5,
            elapsed=60.0,
            duration=180.0,
            next_title="Next Song",
            next_artist="Next Artist",
        )

        assert layout is not None

    def test_uses_solid_transport_icons(self):
        """Player hints and queue status should share the solid icon set."""
        layout = create_player_layout(
            song_title="Test Song",
            artist="Test Artist",
            is_paused=False,
            track_idx=1,
            track_total=5,
            elapsed=60.0,
            duration=180.0,
            next_title="Next Song",
        )

        rendered = self.render(layout)
        assert "◀◀ b" in rendered
        assert "▶ PLAYING" in rendered
        assert "⏸ space" in rendered
        assert "▶▶ n" in rendered
        assert "♪ l" in rendered
        assert "✚ a" in rendered
        assert "▼ d" in rendered
        assert "■ q" in rendered
        assert "▶▶  UP NEXT" in rendered
        assert not {"⏮", "⏯", "⏭", "📜", "➕", "👎", "🚪"} & set(rendered)

    def test_play_pause_callback_receives_new_state(self, monkeypatch):
        """Space should request pause first and resume on the second press."""

        class FakeLive:
            def __init__(self, *_args, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def refresh(self):
                pass

            def update(self, *_args, **_kwargs):
                pass

        class FakePlayer:
            def play(self, *_args):
                return True

            def is_playing(self):
                return True

            def stop(self):
                pass

        keys = iter([" ", " ", "q"])
        states = []
        monkeypatch.setattr("ytm_cli.rich_ui.Live", FakeLive)
        monkeypatch.setattr("ytm_cli.rich_ui.getch_nonblocking", lambda _timeout: next(keys))

        play_with_rich_ui(
            player=FakePlayer(),
            playlist=[{"videoId": "id", "title": "Song"}],
            on_pause=states.append,
        )

        assert states == [True, False]

    def test_play_pause_state_controls_player(self, monkeypatch):
        """The Rich player bridge should map state changes to pause and resume."""
        from ytm_cli.player import play_music_with_controls_rich

        class FakePlayer:
            player_type = "mpv"
            socket_path = None

            def __init__(self):
                self.actions = []

            def is_available(self):
                return True

            def pause(self):
                self.actions.append("pause")

            def resume(self):
                self.actions.append("resume")

            def cleanup(self):
                self.actions.append("cleanup")

        player = FakePlayer()

        def exercise_pause_callback(**kwargs):
            kwargs["on_pause"](True)
            kwargs["on_pause"](False)

        monkeypatch.setattr("ytm_cli.demo.DemoPlayer", lambda: player)
        monkeypatch.setattr("ytm_cli.player.sys.stdin.isatty", lambda: True)
        monkeypatch.setattr("ytm_cli.rich_ui.play_with_rich_ui", exercise_pause_callback)

        play_music_with_controls_rich([{"videoId": "id"}], demo=True)

        assert player.actions == ["pause", "resume", "cleanup"]


class TestProgressBarRendering:
    """Integration tests for progress bar rendering."""

    def test_renders_at_different_progress_points(self):
        """Progress bar should render correctly at various percentages."""
        console = Console(file=StringIO(), width=80)

        test_points = [
            (0, 180),  # 0%
            (54, 180),  # 30%
            (90, 180),  # 50%
            (144, 180),  # 80%
            (179, 180),  # 99%
        ]

        for elapsed, duration in test_points:
            progress = create_progress_bar(elapsed, duration)

            # Should not raise any exceptions
            with console.capture() as capture:
                console.print(progress)

            output = capture.get()
            assert len(output) > 0

    def test_progress_bar_contains_expected_characters(self):
        """Rendered progress should contain progress characters."""
        console = Console(file=StringIO(), width=80)

        progress = create_progress_bar(elapsed=90.0, duration=180.0)

        with console.capture() as capture:
            console.print(progress)

        output = capture.get()

        # Should contain time info
        assert "1:30" in output or "90" in output
        assert "3:00" in output or "180" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
