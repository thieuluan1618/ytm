"""Search widget with input and results table"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Static


class SearchView(Widget):
    """Search interface with input and results table"""

    def compose(self) -> ComposeResult:
        """Create search UI"""
        with Vertical(id="search-container"):
            yield Static("🔍 Search YouTube Music", id="search-title")

            with Container(id="search-input-container"):
                yield Input(
                    placeholder="Search for songs, artists, albums...",
                    id="search-input",
                )
                yield Button("Search", variant="primary", id="search-button")
                yield Button("🤖 LLM", variant="success", id="llm-button")

            # Results table
            yield DataTable(id="search-results", zebra_stripes=True, cursor_type="row")

    def on_mount(self) -> None:
        """Setup the data table"""
        table = self.query_one("#search-results", DataTable)
        table.add_columns("#", "Title", "Artist", "Album", "Duration")
        table.cursor_type = "row"
        table.zebra_stripes = True

    def focus_search(self) -> None:
        """Focus the search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    @on(Input.Submitted, "#search-input")
    def handle_search_submit(self, event: Input.Submitted) -> None:
        """Handle search when Enter is pressed"""
        self.perform_search(event.value)

    @on(Button.Pressed, "#search-button")
    def handle_search_button(self) -> None:
        """Handle search button click"""
        search_input = self.query_one("#search-input", Input)
        self.perform_search(search_input.value)

    @on(Button.Pressed, "#llm-button")
    def handle_llm_button(self) -> None:
        """Handle LLM button click"""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value
        if query:
            self.app.notify(f"LLM search: {query}", severity="information")
            # TODO: Integrate LLM search
        else:
            self.app.notify("Enter a query first", severity="warning")

    def perform_search(self, query: str) -> None:
        """Perform search and update results"""
        if not query:
            return

        self.app.notify(f"Searching for: {query}", severity="information")

        # TODO: Integrate with ytmusic search
        # For now, show placeholder data
        table = self.query_one("#search-results", DataTable)
        table.clear()

        # Mock data for demonstration
        results = [
            ("1", "Example Song", "Example Artist", "Example Album", "3:45"),
            ("2", "Another Song", "Another Artist", "Album Name", "4:12"),
            ("3", "Third Track", "Band Name", "Album Title", "2:58"),
        ]

        for row in results:
            table.add_row(*row)

    @on(DataTable.RowSelected, "#search-results")
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle when a song is selected from results"""
        row_key = event.row_key
        table = self.query_one("#search-results", DataTable)
        row = table.get_row(row_key)

        song_title = row[1]  # Title column
        self.app.notify(f"Selected: {song_title}", severity="information")

        # TODO: Start playing the selected song
