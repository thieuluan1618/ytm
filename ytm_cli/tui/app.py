"""Main Textual application for YTM CLI"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

from .widgets.now_playing import NowPlayingWidget
from .widgets.playlist_sidebar import PlaylistSidebar
from .widgets.queue import QueueWidget
from .widgets.search import SearchView


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

    def compose(self) -> ComposeResult:
        """Create the app layout"""
        yield Header()

        # Main container with split layout
        with Container(id="app-grid"):
            # Left sidebar - playlists
            with Vertical(id="sidebar"):
                yield PlaylistSidebar()

            # Main content area
            with Vertical(id="main-content"):
                # Split between Now Playing and Queue
                with Horizontal(id="player-area"):
                    # Now Playing section (left)
                    with Vertical(id="now-playing-container"):
                        yield NowPlayingWidget()

                    # Queue section (right)
                    with Vertical(id="queue-container"):
                        yield QueueWidget()
        yield SearchView()
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = "YTM CLI"
        self.sub_title = "YouTube Music Terminal Player"

    # Action handlers
    def action_focus_search(self) -> None:
        """Focus the search input"""
        search_view = self.query_one(SearchView)
        search_view.focus_search()

    def action_toggle_play_pause(self) -> None:
        """Toggle play/pause"""
        now_playing = self.query_one(NowPlayingWidget)
        now_playing.toggle_play_pause()

    def action_next_song(self) -> None:
        """Skip to next song"""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.play_song(self.playlist[self.current_index])

    def action_previous_song(self) -> None:
        """Go to previous song"""
        if self.current_index > 0:
            self.current_index -= 1
            self.play_song(self.playlist[self.current_index])

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

        # Update Now Playing widget
        now_playing = self.query_one(NowPlayingWidget)
        now_playing.update_song(song)

        # Update queue
        queue = self.query_one(QueueWidget)
        queue.update_queue(self.playlist, self.current_index)


def run_tui():
    """Entry point to run the Textual TUI"""
    app = YTMApp()
    app.run()


if __name__ == "__main__":
    run_tui()
