"""Main Textual application for YTM CLI"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from ..config import ytmusic
from ..dislikes import dislike_manager
from .player_factory import HybridPlayerService
from .widgets.now_playing import NowPlayingWidget
from .widgets.queue import QueueWidget
from .widgets.search import SearchView, SongSelected


class YTMApp(App):
    """A Textual TUI for YouTube Music CLI"""

    CSS_PATH = "styles.tcss"
    TITLE = "🎵 YTM - YouTube Music CLI"
    SUB_TITLE = "Terminal Music Player"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("slash", "focus_search", "Search", show=True),
        Binding("p", "toggle_play_pause", "Play/Pause", show=True),
        Binding("n", "next_song", "Next", show=True),
        Binding("b", "previous_song", "Previous", show=True),
        Binding("l", "show_lyrics", "Lyrics", show=True),
        Binding("a", "add_to_playlist", "Add", show=True),
        Binding("d", "dislike_song", "Dislike", show=True),
        Binding("question_mark", "show_help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.current_song = None
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.player = HybridPlayerService()

    def compose(self) -> ComposeResult:
        """Create the app layout"""
        # No Header - removed

        # Main vertical layout with content taking up available space and search at bottom
        # with Vertical(id="main-layout"):
        #     # Split between Now Playing and Queue (no sidebar)
        #     # yield NowPlayingWidget()
        #     with Horizontal(id="player-area"):
        #         # Now Playing section (left)
        #         with Vertical(id="now-playing-container"):
        #             yield NowPlayingWidget()

        #         # Queue section (right)
        #         with Vertical(id="queue-container"):
        #             yield QueueWidget()

        #     # Search box at bottom
        #     yield SearchView()

        with Horizontal(id="simple-layout"):
            with Vertical(id="now-playing-container"):
                yield SearchView()

                # Queue section (right)
            with Vertical(id="queue-container"):
                yield NowPlayingWidget()
        # yield Footer()

    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = "YTM CLI"
        self.sub_title = "YouTube Music Terminal Player"

    def on_exit(self) -> None:
        """Clean up resources when app exits"""
        if self.player:
            self.player.cleanup()

    def on_unmount(self) -> None:
        """Called when app is closing - ensure cleanup"""
        if self.player:
            self.player.cleanup()

    def on_song_selected(self, message: SongSelected) -> None:
        """Handle song selection from search results"""
        song = message.song
        self.generate_and_play_radio(song)

    def generate_and_play_radio(self, song: dict) -> None:
        """Generate radio playlist for selected song and start playback"""
        try:
            # Build initial playlist with selected song
            self.playlist = [song]
            self.current_index = 0

            # Show loading notification
            self.notify("🎵 Fetching radio...", severity="information")

            # Generate radio playlist
            try:
                radio = ytmusic.get_watch_playlist(videoId=song.get("videoId"))
                radio_tracks = radio.get("tracks", [])[1:]  # Skip first track (the selected song)

                # Filter out disliked songs from radio
                original_radio_count = len(radio_tracks)
                filtered_radio = dislike_manager.filter_disliked_songs(radio_tracks)
                filtered_radio_count = original_radio_count - len(filtered_radio)

                if filtered_radio_count > 0:
                    self.notify(
                        f"Filtered out {filtered_radio_count} disliked song(s)",
                        severity="information",
                    )

                self.playlist.extend(filtered_radio)
                self.notify(f"✓ Ready to play: {len(self.playlist)} songs", severity="information")

            except Exception as e:
                self.notify(
                    f"Error fetching radio: {str(e)}. Playing selected song only.", severity="error"
                )

            # Start playback
            self.play_song(song)

        except Exception as e:
            self.notify(f"Error starting playback: {str(e)}", severity="error")

    # Action handlers
    def action_quit(self) -> None:
        """Quit app and stop music"""
        self.player.cleanup()
        self.exit()

    def action_focus_search(self) -> None:
        """Focus the search input"""
        search_view = self.query_one(SearchView)
        search_view.focus_search()

    def action_toggle_play_pause(self) -> None:
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
            self.is_playing = False
        else:
            self.player.resume()
            self.is_playing = True

        now_playing = self.query_one(NowPlayingWidget)
        now_playing.toggle_play_pause()

    def action_next_song(self) -> None:
        """Skip to next song"""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.player.stop()  # Stop current playback
            self.play_song(self.playlist[self.current_index])
        else:
            self.notify("Already at last song", severity="warning")

    def action_previous_song(self) -> None:
        """Go to previous song"""
        if self.current_index > 0:
            self.current_index -= 1
            self.player.stop()  # Stop current playback
            self.play_song(self.playlist[self.current_index])
        else:
            self.notify("Already at first song", severity="warning")

    def action_show_lyrics(self) -> None:
        """Show lyrics for current song"""
        # TODO: Implement lyrics display
        self.notify("Lyrics feature coming soon!", severity="information")

    def action_add_to_playlist(self) -> None:
        """Add current song to a playlist"""
        # TODO: Implement add to playlist
        self.notify("Add to playlist feature coming soon!", severity="information")

    def action_dislike_song(self) -> None:
        """Dislike current song"""
        # TODO: Implement dislike
        self.notify("Dislike feature coming soon!", severity="information")

    def action_show_help(self) -> None:
        """Show help screen"""
        # TODO: Implement help modal
        self.notify("Press ? to show keyboard shortcuts", severity="information")

    def play_song(self, song: dict) -> None:
        """Play a song"""
        self.current_song = song
        self.is_playing = True

        # Update UI first
        try:
            # Update Now Playing widget
            now_playing = self.query_one(NowPlayingWidget)
            now_playing.update_song(song)

            # Update queue
            queue = self.query_one(QueueWidget)
            queue.update_queue(self.playlist, self.current_index)

        except Exception as e:
            self.notify(f"Error updating UI: {str(e)}", severity="error")
            import traceback

            traceback.print_exc()

        # Check if player is available
        if not self.player.is_available():
            self.notify(
                "❌ No audio player available. Install mpv or FFmpeg.",
                severity="error",
            )
            return

        # Start audio playback
        video_id = song.get("videoId")
        title = song.get("title", "Unknown")

        if video_id:
            success = self.player.play(video_id, title)
            if not success:
                self.notify("Error starting playback", severity="error")
                return
            player_info = self.player.get_player_info()
            self.notify(
                f"▶ Playing: {title} ({player_info['type']})",
                severity="information",
            )
        else:
            self.notify("No video ID available for this song", severity="warning")
            return


def run_tui():
    """Entry point to run the Textual TUI"""
    app = YTMApp()
    app.run()


if __name__ == "__main__":
    run_tui()
