"""Search widget with input and results table"""

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input

from ...config import ytmusic
from ...dislikes import dislike_manager
from ...llm_client import LLMClient


class SongSelected(Message):
    """Message emitted when a song is selected from search results"""

    def __init__(self, song: dict) -> None:
        self.song = song
        super().__init__()


class SearchView(Widget):
    """Search interface with input and results table"""

    def __init__(self):
        super().__init__()
        self.search_results = []
        self.llm_client = LLMClient()

    def compose(self) -> ComposeResult:
        """Create search UI"""
        with Vertical(id="search-container"):
            # yield Static("🔍 Search YouTube Music", id="search-title")

            # Row 1: Search input
            yield Input(
                placeholder="Search for songs, artists, albums...",
                id="search-input",
            )

            # Row 2: Buttons
            with Container(id="search-button-container"):
                yield Button("🔍", variant="primary", id="search-button")
                yield Button("🤖 Ay AI", variant="success", id="llm-button")

            # Results table
            yield DataTable(id="search-results", zebra_stripes=True, cursor_type="row")

    def on_mount(self) -> None:
        """Setup the data table"""
        table = self.query_one("#search-results", DataTable)
        table.add_columns("#", "Title", "Artist")
        table.cursor_type = "row"
        table.zebra_stripes = True

    def focus_search(self) -> None:
        """Focus the search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    @on(Input.Submitted, "#search-input")
    def handle_search_submit(self, event: Input.Submitted) -> None:
        """Handle search when Enter is pressed"""
        self.perform_search_worker(event.value)

    @on(Button.Pressed, "#search-button")
    def handle_search_button(self) -> None:
        """Handle search button click"""
        search_input = self.query_one("#search-input", Input)
        self.perform_search_worker(search_input.value)

    @on(Button.Pressed, "#llm-button")
    def handle_llm_button(self) -> None:
        """Handle LLM button click"""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value
        if query:
            self.perform_llm_search_worker(query)
        else:
            self.app.notify("Enter a query first", severity="warning")

    @work(exclusive=True)
    async def perform_llm_search_worker(self, query: str) -> None:
        """Perform LLM search as async worker"""
        self.perform_llm_search(query)

    def perform_llm_search(self, query: str) -> None:
        """Perform LLM-enhanced search"""
        try:
            self.app.notify("🤖 Consulting AI...", severity="information")

            # Call LLM to get search parameters
            llm_response = self.llm_client.generate(query)

            if not llm_response:
                self.app.notify("LLM request failed, using direct search", severity="warning")
                self.perform_search(query)
                return

            # Extract the search query from LLM response
            search_query = llm_response.query
            notes = llm_response.parameters.get("notes", "")

            if notes:
                self.app.notify(f"AI: {notes}", severity="information")

            self.app.notify(f"🔍 Searching: {search_query}", severity="information")

            # Perform search with the LLM-generated query
            self.perform_search(search_query)

        except Exception as e:
            self.app.notify(f"LLM error: {str(e)}", severity="error")

    @work(exclusive=True)
    async def perform_search_worker(self, query: str) -> None:
        """Perform search as async worker"""
        self.perform_search(query)

    def perform_search(self, query: str) -> None:
        """Perform search and update results"""
        if not query:
            return

        self.app.notify(f"🔍 Searching for: {query}", severity="information")

        try:
            # Search YouTube Music
            results = ytmusic.search(query, filter="songs")

            if not results:
                self.app.notify("No songs found", severity="warning")
                return

            # Filter out disliked songs
            original_count = len(results)
            filtered_results = dislike_manager.filter_disliked_songs(results)
            filtered_count = original_count - len(filtered_results)

            if filtered_count > 0:
                self.app.notify(
                    f"Filtered out {filtered_count} disliked song(s)", severity="information"
                )

            if not filtered_results:
                self.app.notify("No songs found after filtering dislikes", severity="warning")
                return

            # Store results for later use
            self.search_results = filtered_results

            # Update results table
            table = self.query_one("#search-results", DataTable)
            table.clear()

            for idx, song in enumerate(filtered_results, 1):
                title = song.get("title", "Unknown Title")
                artist = (
                    song.get("artists", [{}])[0].get("name", "Unknown Artist")
                    if song.get("artists")
                    else "Unknown Artist"
                )

                table.add_row(str(idx), title, artist)

            self.app.notify(f"✓ Found {len(filtered_results)} songs", severity="information")

        except Exception as e:
            self.app.notify(f"Search error: {str(e)}", severity="error")

    @on(DataTable.RowSelected, "#search-results")
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle when a song is selected from results"""
        row_index = event.cursor_row

        if 0 <= row_index < len(self.search_results):
            song = self.search_results[row_index]
            song_title = song.get("title", "Unknown")
            self.app.notify(f"▶ Starting playback: {song_title}", severity="information")

            # Emit message to trigger playback
            self.post_message(SongSelected(song))
