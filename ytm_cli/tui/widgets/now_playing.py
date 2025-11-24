"""Now Playing widget with song info and controls"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, ProgressBar, Static


class NowPlayingWidget(Widget):
    """Displays currently playing song with controls"""

    song_title = reactive("No song playing")
    artist_name = reactive("---")
    album_name = reactive("---")
    current_time = reactive("0:00")
    total_time = reactive("0:00")
    progress = reactive(0.0)
    is_playing = reactive(False)

    def compose(self) -> ComposeResult:
        """Create now playing UI"""
        with Vertical(id="now-playing"):
            yield Static("🎵 Now Playing", id="now-playing-title")

            # Song info
            with Container(id="song-info"):
                yield Label("No song playing", id="song-title-display")
                yield Label("---", id="artist-display")
                yield Label("---", id="album-display")

            # Progress bar
            with Container(id="progress-container"):
                yield ProgressBar(id="progress-bar", total=100)
                with Horizontal(id="time-display"):
                    yield Label("0:00", id="current-time")
                    yield Label("0:00", id="total-time")

            # Playback controls
            with Horizontal(id="playback-controls"):
                yield Button("⏮", id="btn-prev", variant="default")
                yield Button("⏯", id="btn-play-pause", variant="primary")
                yield Button("⏭", id="btn-next", variant="default")
                yield Button("🔀", id="btn-shuffle", variant="default")
                yield Button("🔁", id="btn-repeat", variant="default")

            # Additional controls
            with Horizontal(id="additional-controls"):
                yield Button("❤️", id="btn-like", variant="success")
                yield Button("👎", id="btn-dislike", variant="error")
                yield Button("📝", id="btn-add-playlist", variant="default")
                yield Button("📜", id="btn-lyrics", variant="default")

    def on_mount(self) -> None:
        """Initialize display when widget mounts"""
        # Manually trigger initial UI update
        try:
            label = self.query_one("#song-title-display", Label)
            label.update(f"[bold cyan]{self.song_title}[/bold cyan]")

            label = self.query_one("#artist-display", Label)
            label.update(f"👤 [yellow]{self.artist_name}[/yellow]")

            label = self.query_one("#album-display", Label)
            label.update(f"💿 [dim]{self.album_name}[/dim]")

            label = self.query_one("#current-time", Label)
            label.update(self.current_time)

            label = self.query_one("#total-time", Label)
            label.update(self.total_time)
        except Exception as e:
            self.app.notify(f"Error in NowPlaying.on_mount: {str(e)}", severity="error")

    def watch_song_title(self, title: str) -> None:
        """Update song title display"""
        try:
            label = self.query_one("#song-title-display", Label)
            label.update(f"[bold cyan]{title}[/bold cyan]")
        except Exception as e:
            self.app.notify(f"✗ Title update failed: {e}", severity="error")

    def watch_artist_name(self, artist: str) -> None:
        """Update artist display"""
        try:
            label = self.query_one("#artist-display", Label)
            label.update(f"👤 [yellow]{artist}[/yellow]")
        except Exception as e:
            self.app.notify(f"✗ Artist update failed: {e}", severity="error")

    def watch_album_name(self, album: str) -> None:
        """Update album display"""
        try:
            label = self.query_one("#album-display", Label)
            label.update(f"💿 [dim]{album}[/dim]")
        except Exception as e:
            self.app.notify(f"✗ Album update failed: {e}", severity="error")

    def watch_progress(self, progress_value: float) -> None:
        """Update progress bar"""
        try:
            progress_bar = self.query_one("#progress-bar", ProgressBar)
            progress_bar.update(progress=progress_value)
        except Exception:
            pass  # Widget not mounted yet

    def watch_current_time(self, time_str: str) -> None:
        """Update current time display"""
        try:
            label = self.query_one("#current-time", Label)
            label.update(time_str)
        except Exception:
            pass  # Widget not mounted yet

    def watch_total_time(self, time_str: str) -> None:
        """Update total time display"""
        try:
            label = self.query_one("#total-time", Label)
            label.update(time_str)
        except Exception:
            pass  # Widget not mounted yet

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn-play-pause":
            self.toggle_play_pause()
        elif button_id == "btn-prev":
            self.app.action_previous_song()
        elif button_id == "btn-next":
            self.app.action_next_song()
        elif button_id == "btn-shuffle":
            self.app.notify("Shuffle mode", severity="information")
        elif button_id == "btn-repeat":
            self.app.notify("Repeat mode", severity="information")
        elif button_id == "btn-like":
            self.app.notify("❤️ Liked!", severity="information")
        elif button_id == "btn-dislike":
            self.app.action_dislike_song()
        elif button_id == "btn-add-playlist":
            self.app.action_add_to_playlist()
        elif button_id == "btn-lyrics":
            self.app.action_show_lyrics()

    def toggle_play_pause(self) -> None:
        """Toggle play/pause state"""
        self.is_playing = not self.is_playing
        button = self.query_one("#btn-play-pause", Button)
        button.label = "⏸" if self.is_playing else "▶"
        status = "Playing" if self.is_playing else "Paused"
        self.app.notify(status, severity="information")

    def update_song(self, song: dict) -> None:
        """Update displayed song information"""
        title = song.get("title", "Unknown Title")
        artist = (
            song.get("artists", [{}])[0].get("name", "Unknown Artist")
            if song.get("artists")
            else "Unknown Artist"
        )
        album = (
            song.get("album", {}).get("name", "Unknown Album")
            if song.get("album")
            else "Unknown Album"
        )

        # Update reactive properties (these should trigger watchers)
        self.song_title = title
        self.artist_name = artist
        self.album_name = album

        # TODO: Get actual duration from song
        self.total_time = song.get("duration", "0:00")
        self.current_time = "0:00"
        self.progress = 0.0
        self.is_playing = True

        # Force a refresh to ensure UI updates
        self.refresh()
