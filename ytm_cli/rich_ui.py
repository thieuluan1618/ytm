"""Rich-based terminal UI components for ytm-cli.

This module provides a rich-based alternative to the curses UI,
starting with the progress bar and player interface.
"""

import select
import sys
import termios
import time
import tty
from collections.abc import Callable

from rich.align import Align
from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, ProgressColumn, Task, TextColumn
from rich.table import Table
from rich.text import Text

from .utils import NEXT_ICON, PAUSE_ICON, PLAY_ICON, PREVIOUS_ICON, player_controls


class CustomProgressBar(ProgressColumn):
    """Custom progress bar that mimics the curses style with ━●─ characters."""

    def render(self, task: Task) -> RenderableType:
        """Render a progress bar with heavy line (━), playhead (●), and light line (─)."""
        if task.total is None or task.total <= 0:
            # No duration, show empty bar
            return Text("─" * 40, style="dim")

        # Calculate progress
        completed = task.completed if task.completed is not None else 0
        percentage = completed / task.total
        width = 40  # Fixed width for consistency

        # Calculate playhead position
        filled = int(percentage * (width - 1))
        filled = max(0, min(filled, width - 1))

        # Match the shared YTM accent used by the curses screens.
        text = Text()
        if filled > 0:
            text.append("━" * filled, style="yellow bold")
        text.append("●", style="yellow bold")
        if filled < width - 1:
            text.append("─" * (width - filled - 1), style="dim")

        return text


def create_progress_bar(elapsed: float | None, duration: float | None) -> Progress:
    """Create a rich Progress bar for music playback.

    Args:
        elapsed: Current playback position in seconds
        duration: Total track duration in seconds

    Returns:
        Configured Progress instance
    """
    progress = Progress(
        TextColumn("[bold]{task.fields[time_str]}[/bold]"),
        CustomProgressBar(),
        TextColumn("[dim]{task.fields[percent]}[/dim]"),
        expand=False,
    )

    # Format time strings
    def fmt_time(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"

    elapsed = elapsed or 0.0
    duration = duration or 0.0
    percent_val = int(elapsed / duration * 100) if duration > 0 else 0

    time_str = f"{fmt_time(elapsed)} / {fmt_time(duration)}"
    percent_str = f"{percent_val}%"

    progress.add_task(
        "",
        total=duration if duration > 0 else 100,
        completed=elapsed if duration > 0 else 0,
        time_str=time_str,
        percent=percent_str,
    )

    return progress


def create_player_layout(
    song_title: str,
    artist: str,
    is_paused: bool,
    track_idx: int,
    track_total: int,
    elapsed: float | None,
    duration: float | None,
    toast_msg: str | None = None,
    toast_detail: str | None = None,
    next_title: str | None = None,
    next_artist: str | None = None,
) -> Layout:
    """Create the full player layout using rich.

    Args:
        song_title: Current song title
        artist: Artist name
        is_paused: Whether playback is paused
        track_idx: Current track number (1-indexed)
        track_total: Total tracks in queue
        elapsed: Current playback position in seconds
        duration: Total track duration in seconds
        toast_msg: Optional toast notification message
        toast_detail: Optional toast detail line
        next_title: Next track title
        next_artist: Next track artist

    Returns:
        Rich Layout ready to render
    """
    layout = Layout()
    content = Layout()

    # Shared brand header, playback state, and queue position.
    state = f"{PAUSE_ICON} PAUSED" if is_paused else f"{PLAY_ICON} PLAYING"
    position = f"{track_idx} / {track_total}"
    header = Table.grid(expand=True)
    header.add_column(justify="left", no_wrap=True)
    header.add_column(justify="right", no_wrap=True)
    header.add_row(
        Text.assemble(("YTM", "yellow bold"), (" // PLAYER", "dim")),
        Text.assemble((state, "yellow"), (f"  {position}", "dim")),
    )

    # Song info
    song_info = Table.grid(padding=(0, 1))
    song_info.add_column(justify="center")
    song_info.add_row(Text("NOW PLAYING", style="yellow"))
    song_info.add_row(Text(song_title, style="bold"))
    song_info.add_row(Text(artist, style="dim"))

    # Progress bar
    progress = create_progress_bar(elapsed, duration)

    # Queue context or toast
    footer_content = ""
    if toast_msg:
        footer_parts = [("STATUS  ", "yellow"), (toast_msg, "bold")]
        if toast_detail:
            footer_parts.append(("\n        ", ""))
            footer_parts.append((toast_detail, "dim"))
        footer_content = Text.assemble(*footer_parts)
    elif next_title:
        next_info = f"{next_title}"
        if next_artist:
            next_info += f" · {next_artist}"
        footer_content = Text.assemble(
            (f"{NEXT_ICON}  UP NEXT  ", "yellow"),
            (next_info, "dim"),
        )
    else:
        footer_content = ""

    # Keep transport and library actions readable on separate scan lines.
    def control_line(items):
        parts = []
        for i, (icon, key, description) in enumerate(items):
            if i:
                parts.append(("   ", ""))
            key = key.upper()
            parts.extend(
                [
                    (f"{icon} [{key}]", "yellow"),
                    (f" {description}", "dim"),
                ]
            )
        return Text.assemble(*parts)

    control_items = player_controls(is_paused)
    controls = Table.grid(expand=True)
    controls.add_column(justify="center")
    controls.add_row(control_line(control_items[:3]))
    controls.add_row(control_line(control_items[3:]))

    # Keep every player section inside one continuous frame.
    content.split_column(
        Layout(header, size=1),
        Layout(Align.center(song_info, vertical="middle"), size=5),
        Layout(Align.center(progress), size=1),
        Layout(Align.center(footer_content) if footer_content else "", size=2),
        Layout(controls, size=2),
    )
    layout.update(Panel(content, border_style="dim", padding=(0, 1)))

    return layout


def render_player_frame(
    console: Console,
    song_title: str,
    artist: str,
    is_paused: bool,
    track_idx: int,
    track_total: int,
    elapsed: float | None,
    duration: float | None,
    toast_msg: str | None = None,
    toast_detail: str | None = None,
    next_title: str | None = None,
    next_artist: str | None = None,
) -> None:
    """Render a single frame of the player UI.

    This is a simple version that prints the layout. For live updates,
    use with rich.Live context manager.

    Note: Removed console.clear() to prevent flickering. Use rich.Live instead.
    """
    layout = create_player_layout(
        song_title=song_title,
        artist=artist,
        is_paused=is_paused,
        track_idx=track_idx,
        track_total=track_total,
        elapsed=elapsed,
        duration=duration,
        toast_msg=toast_msg,
        toast_detail=toast_detail,
        next_title=next_title,
        next_artist=next_artist,
    )
    # Don't clear - let rich.Live handle updates
    console.print(layout)


# Demo function for testing
def demo_player():
    """Demo the rich-based player UI."""
    console = Console()

    with Live(
        create_player_layout(
            song_title="Neon Cruise",
            artist="Synthwave Demo Band",
            is_paused=False,
            track_idx=2,
            track_total=8,
            elapsed=0,
            duration=180,
        ),
        console=console,
        screen=True,
        transient=False,
        auto_refresh=False,  # Drive refresh manually to prevent flicker
    ) as live:
        live.refresh()  # Paint the initial frame once
        for i in range(0, 180, 1):  # Update every second instead of 0.1s
            time.sleep(1.0)
            layout = create_player_layout(
                song_title="Neon Cruise",
                artist="Synthwave Demo Band",
                is_paused=False,
                track_idx=2,
                track_total=8,
                elapsed=i,
                duration=180,
                next_title="Next Track" if i > 60 else None,
                next_artist="Next Artist" if i > 60 else None,
            )
            live.update(layout, refresh=True)


def getch_nonblocking(timeout: float = 0.0) -> str | None:
    """Get a single character from stdin without blocking.

    Args:
        timeout: Maximum time to wait for input in seconds (0 = non-blocking)

    Returns:
        Character if available, None otherwise
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Use select to check if input is available
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            ch = sys.stdin.read(1)
            return ch
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def play_with_rich_ui(
    player,
    playlist: list[dict],
    playlist_name: str | None = None,
    get_elapsed: Callable[[], float | None] | None = None,
    get_duration: Callable[[], float | None] | None = None,
    on_next: Callable[[], None] | None = None,
    on_previous: Callable[[], None] | None = None,
    on_pause: Callable[[bool], None] | None = None,
    on_lyrics: Callable[[dict], None] | None = None,
    on_add_playlist: Callable[[dict], None] | None = None,
    on_dislike: Callable[[dict], None] | None = None,
) -> None:
    """Play music with rich-based UI.

    This is a simplified version for initial integration. Full feature parity
    with curses player will be added incrementally.

    Args:
        player: The player instance (MPV or FFmpeg)
        playlist: List of song dictionaries
        playlist_name: Optional playlist name
        get_elapsed: Function to get current playback position
        get_duration: Function to get track duration
        on_next: Callback for next track
        on_previous: Callback for previous track
        on_pause: Callback receiving the desired paused state
        on_lyrics: Callback for lyrics display
        on_add_playlist: Callback for adding to playlist
        on_dislike: Callback for disliking song
    """
    console = Console()

    if not playlist:
        console.print("[red]No songs to play[/red]")
        return

    current_idx = 0
    is_paused = False
    toast_msg = None
    toast_detail = None
    toast_expire = 0

    console.print(f"[cyan]🎵 Playing {len(playlist)} tracks...[/cyan]\n")

    while current_idx < len(playlist):
        song = playlist[current_idx]
        song_title = song.get("title", "Unknown")
        artist = (
            song.get("artists", [{"name": "Unknown"}])[0]["name"]
            if song.get("artists")
            else "Unknown"
        )

        # Start playback
        video_id = song.get("videoId")
        if not video_id:
            current_idx += 1
            continue

        if not player.play(video_id, song_title):
            console.print(f"[red]Failed to play: {song_title}[/red]")
            current_idx += 1
            continue

        # Create initial layout
        layout = create_player_layout(
            song_title=song_title,
            artist=artist,
            is_paused=is_paused,
            track_idx=current_idx + 1,
            track_total=len(playlist),
            elapsed=0,
            duration=None,
            toast_msg=toast_msg,
            toast_detail=toast_detail,
        )

        with Live(
            layout,
            console=console,
            screen=True,
            transient=False,
            auto_refresh=False,  # Drive refresh manually to prevent flicker
        ) as live:
            live.refresh()  # Paint the initial frame once
            last_elapsed = None

            while player.is_playing():
                # Get playback info
                elapsed = get_elapsed() if get_elapsed else None
                duration = get_duration() if get_duration else None

                # Only update if values changed significantly (reduce flickering)
                elapsed_changed = (
                    (elapsed is None and last_elapsed is not None)
                    or (elapsed is not None and last_elapsed is None)
                    or (
                        elapsed is not None
                        and last_elapsed is not None
                        and abs(elapsed - last_elapsed) >= 0.5
                    )
                )

                # Clear expired toast
                toast_changed = False
                if toast_msg and time.time() >= toast_expire:
                    toast_msg = None
                    toast_detail = None
                    toast_changed = True

                # Check for keyboard input (longer timeout to reduce CPU)
                key = getch_nonblocking(0.1)
                if key:
                    if key == " ":
                        is_paused = not is_paused
                        if on_pause:
                            on_pause(is_paused)
                        toast_msg = f"{PAUSE_ICON} Paused" if is_paused else f"{PLAY_ICON} Resumed"
                        toast_expire = time.time() + 1.5
                    elif key == "n":
                        if on_next:
                            on_next()
                        player.stop()
                        toast_msg = f"{NEXT_ICON} Next"
                        toast_expire = time.time() + 1.5
                        break
                    elif key == "b":
                        if on_previous:
                            on_previous()
                        current_idx = max(0, current_idx - 1)
                        player.stop()
                        toast_msg = f"{PREVIOUS_ICON} Previous"
                        toast_expire = time.time() + 1.5
                        break
                    elif key == "l":
                        if on_lyrics:
                            live.stop()
                            on_lyrics(song)
                            live.start(refresh=True)
                    elif key == "a":
                        if on_add_playlist:
                            live.stop()
                            result = on_add_playlist(song)
                            live.start(refresh=True)
                            if result:
                                toast_msg = f"Added · {song_title} · {artist}"
                                toast_detail = f"Saved to playlist · {result}"
                                toast_expire = time.time() + 3.5
                            elif result is False:
                                toast_msg = f"Could not add · {song_title}"
                                toast_detail = "The track may already be saved in that playlist"
                                toast_expire = time.time() + 3.5
                            else:
                                toast_msg = "Add cancelled"
                                toast_expire = time.time() + 1.5
                    elif key == "d":
                        if on_dislike:
                            on_dislike(song)
                        toast_msg = f"Disliked · {song_title} · {artist}"
                        toast_detail = "Hidden from future searches and radio playlists"
                        toast_expire = time.time() + 3.5
                        player.stop()
                        break
                    elif key == "q" or key == "\x03":  # q or Ctrl+C
                        player.stop()
                        return

                # Update layout only if something changed
                if elapsed_changed or key or toast_changed:
                    last_elapsed = elapsed

                    # Update layout
                    next_title = None
                    next_artist = None
                    if current_idx + 1 < len(playlist):
                        next_song = playlist[current_idx + 1]
                        next_title = next_song.get("title", "Unknown")
                        next_artist = (
                            next_song.get("artists", [{"name": "Unknown"}])[0]["name"]
                            if next_song.get("artists")
                            else "Unknown"
                        )

                    layout = create_player_layout(
                        song_title=song_title,
                        artist=artist,
                        is_paused=is_paused,
                        track_idx=current_idx + 1,
                        track_total=len(playlist),
                        elapsed=elapsed,
                        duration=duration,
                        toast_msg=toast_msg,
                        toast_detail=toast_detail,
                        next_title=next_title,
                        next_artist=next_artist,
                    )

                    live.update(layout, refresh=True)

        # Move to next track
        current_idx += 1

    console.print("\n[green]✅ Playback complete![/green]")


if __name__ == "__main__":
    demo_player()
