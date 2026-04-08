"""Queue widget showing upcoming songs"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static


class QueueWidget(Widget):
    """Displays the playback queue"""

    def compose(self) -> ComposeResult:
        """Create queue UI"""
        with Vertical(id="queue"):
            yield Static("📻 Queue", id="queue-title")
            with VerticalScroll(id="queue-scroll"):
                yield ListView(id="queue-list")

    def on_mount(self) -> None:
        """Initialize empty queue display"""
        queue_list = self.query_one("#queue-list", ListView)
        queue_list.append(ListItem(Static("[dim]Queue is empty - Search and play a song[/dim]")))

    def update_queue(self, playlist: list, current_index: int) -> None:
        """Update the queue display"""
        try:
            queue_list = self.query_one("#queue-list", ListView)
            queue_list.clear()

            if not playlist:
                queue_list.append(ListItem(Static("[dim]Queue is empty[/dim]")))
                return

            for i, song in enumerate(playlist):
                title = song.get("title", "Unknown")
                artist = (
                    song.get("artists", [{}])[0].get("name", "Unknown")
                    if song.get("artists")
                    else "Unknown"
                )

                if i == current_index:
                    # Current song - highlighted
                    item_text = (
                        f"[bold green]► {i + 1}. {title}[/bold green]\n   [dim]{artist}[/dim]"
                    )
                elif i < current_index:
                    # Already played - dimmed
                    item_text = f"[dim]{i + 1}. {title}\n   {artist}[/dim]"
                else:
                    # Upcoming songs
                    item_text = f"[cyan]{i + 1}. {title}[/cyan]\n   [yellow]{artist}[/yellow]"

                queue_list.append(ListItem(Static(item_text)))

            # Force refresh
            self.refresh()

        except Exception as e:
            self.app.notify(f"✗ Queue update failed: {e}", severity="error")
            import traceback

            traceback.print_exc()

    def add_placeholder_songs(self) -> None:
        """Add placeholder songs for demonstration"""
        mock_playlist = [
            {"title": "Current Song", "artists": [{"name": "Artist Name"}]},
            {"title": "Next Song", "artists": [{"name": "Another Artist"}]},
            {"title": "Third Song", "artists": [{"name": "Band Name"}]},
            {"title": "Fourth Song", "artists": [{"name": "Singer Name"}]},
        ]
        self.update_queue(mock_playlist, 0)
