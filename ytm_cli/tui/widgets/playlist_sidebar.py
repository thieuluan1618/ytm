"""Playlist sidebar widget"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, ListItem, ListView, Static


class PlaylistSidebar(Widget):
    """Sidebar showing user playlists"""

    def compose(self) -> ComposeResult:
        """Create playlist sidebar UI"""
        with Vertical(id="playlist-sidebar"):
            yield Static("📝 Playlists", id="sidebar-title")

            with VerticalScroll(id="playlist-scroll"):
                yield ListView(id="playlist-list")

            yield Button("+ New Playlist", id="btn-new-playlist", variant="success")

    def on_mount(self) -> None:
        """Initialize with placeholder playlists"""
        self.load_playlists()

    def load_playlists(self) -> None:
        """Load playlists from playlist manager"""
        playlist_list = self.query_one("#playlist-list", ListView)
        playlist_list.clear()

        # TODO: Load actual playlists from playlist_manager
        # For now, show placeholders
        mock_playlists = [
            {"name": "My Favorites", "count": 12},
            {"name": "Workout Mix", "count": 8},
            {"name": "Chill Vibes", "count": 15},
            {"name": "Vietnamese Pop", "count": 20},
        ]

        for playlist in mock_playlists:
            name = playlist["name"]
            count = playlist["count"]
            item_text = f"[cyan]{name}[/cyan]\n[dim]{count} songs[/dim]"
            playlist_list.append(ListItem(Static(item_text)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle playlist selection"""
        # TODO: Load and play selected playlist
        self.app.notify("Playlist selected", severity="information")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-new-playlist":
            self.create_new_playlist()

    def create_new_playlist(self) -> None:
        """Create a new playlist"""
        # TODO: Show input dialog for playlist name
        self.app.notify("Create new playlist", severity="information")
