"""Enhanced verbose logging for YTM CLI with rich formatting"""

import time
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

console = Console()

# Global verbose state
_VERBOSE = False
_VERBOSE_FILE = None


def set_verbose(enabled: bool, log_file: Optional[str] = None):
    """Set verbose mode and optional log file"""
    global _VERBOSE, _VERBOSE_FILE
    _VERBOSE = enabled
    _VERBOSE_FILE = log_file


def is_verbose() -> bool:
    """Check if verbose mode is enabled"""
    return _VERBOSE


def log_to_file(message: str):
    """Write message to log file if specified"""
    if _VERBOSE_FILE:
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(_VERBOSE_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass


def log_section(title: str, emoji: str = "📋"):
    """Log a section header"""
    if not _VERBOSE:
        return

    separator = "─" * 60
    console.print(f"\n[bold cyan]{separator}[/bold cyan]")
    console.print(f"[bold cyan]{emoji} {title}[/bold cyan]")
    console.print(f"[bold cyan]{separator}[/bold cyan]")
    log_to_file(f"\n{separator}\n{emoji} {title}\n{separator}")


def log_step(step: str, detail: str = ""):
    """Log a step in the process"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    if detail:
        console.print(f"[dim]{timestamp}[/dim] [cyan]▶[/cyan] {step}: [yellow]{detail}[/yellow]")
        log_to_file(f"{timestamp} ▶ {step}: {detail}")
    else:
        console.print(f"[dim]{timestamp}[/dim] [cyan]▶[/cyan] {step}")
        log_to_file(f"{timestamp} ▶ {step}")


def log_info(message: str):
    """Log informational message"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim]   [blue]ℹ[/blue] [dim]{message}[/dim]")
    log_to_file(f"{timestamp}   ℹ {message}")


def log_success(message: str):
    """Log success message"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim]   [green]✓[/green] [green]{message}[/green]")
    log_to_file(f"{timestamp}   ✓ {message}")


def log_warning(message: str):
    """Log warning message"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim]   [yellow]⚠[/yellow] [yellow]{message}[/yellow]")
    log_to_file(f"{timestamp}   ⚠ {message}")


def log_error(message: str):
    """Log error message"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim]   [red]✗[/red] [red]{message}[/red]")
    log_to_file(f"{timestamp}   ✗ {message}")


def log_search_results(query: str, results: List[Dict], filtered_count: int = 0):
    """Log search results in a formatted table"""
    if not _VERBOSE:
        return

    log_section("Search Results", "🔍")
    log_step("Query", query)
    log_info(f"Total results: {len(results) + filtered_count}")

    if filtered_count > 0:
        log_warning(f"Filtered {filtered_count} disliked song(s)")

    if len(results) > 0:
        table = Table(show_header=True, header_style="bold magenta", show_lines=False)
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan")
        table.add_column("Artist", style="yellow")
        table.add_column("Album", style="green", max_width=30)
        table.add_column("Duration", style="dim", width=8)

        for i, song in enumerate(results[:10], 1):
            title = song.get("title", "Unknown")
            artist = (
                song.get("artists", [{}])[0].get("name", "Unknown")
                if song.get("artists")
                else "Unknown"
            )
            album = song.get("album", {}).get("name", "") if song.get("album") else ""
            duration = song.get("duration", "")

            table.add_row(str(i), title[:40], artist[:30], album[:30], duration)

        if len(results) > 10:
            table.add_row("...", f"+ {len(results) - 10} more", "", "", "")

        console.print(table)
        log_to_file(f"Displayed search results table with {min(10, len(results))} items")


def log_radio_generation(video_id: str, radio_tracks: int, filtered: int = 0):
    """Log radio playlist generation"""
    if not _VERBOSE:
        return

    log_section("Radio Playlist Generation", "📻")
    log_step("Video ID", video_id)
    log_info("Fetching watch playlist from YouTube Music API...")
    log_success(f"Received {radio_tracks} radio tracks")

    if filtered > 0:
        log_warning(f"Filtered {filtered} disliked song(s) from radio")
        log_info(f"Final radio playlist: {radio_tracks - filtered} tracks")


def log_playlist_composition(playlist: List[Dict], selected_song_index: int = 0):
    """Log the final playlist composition"""
    if not _VERBOSE:
        return

    log_section("Playlist Composition", "📝")

    tree = Tree("[bold cyan]Playback Queue[/bold cyan]")

    for i, song in enumerate(playlist[:15]):
        title = song.get("title", "Unknown")
        artist = (
            song.get("artists", [{}])[0].get("name", "Unknown")
            if song.get("artists")
            else "Unknown"
        )

        if i == selected_song_index:
            tree.add(f"[bold green]► {i + 1}. {title} - {artist}[/bold green]")
        else:
            tree.add(f"[dim]{i + 1}. {title} - {artist}[/dim]")

    if len(playlist) > 15:
        tree.add(f"[dim]... + {len(playlist) - 15} more tracks[/dim]")

    console.print(tree)
    log_info(f"Total tracks in queue: {len(playlist)}")
    log_to_file(f"Playlist has {len(playlist)} tracks")


def log_mpv_start(video_id: str, title: str, artist: str, socket_path: str, pid: int):
    """Log MPV process start"""
    if not _VERBOSE:
        return

    log_section("MPV Player", "🎵")
    log_step("Starting MPV process")
    log_info(f"Title: {title}")
    log_info(f"Artist: {artist}")
    log_info(f"Video ID: {video_id}")
    log_info(f"IPC Socket: {socket_path}")
    log_success(f"MPV started (PID: {pid})")


def log_mpv_stop(exit_code: int, reason: str = ""):
    """Log MPV process stop"""
    if not _VERBOSE:
        return

    if exit_code == 0:
        log_success(f"MPV exited normally (code: {exit_code})")
    else:
        log_warning(f"MPV exited with code: {exit_code}")

    if reason:
        log_info(f"Reason: {reason}")


def log_song_change(index: int, total: int, song: Dict):
    """Log song change in playlist"""
    if not _VERBOSE:
        return

    title = song.get("title", "Unknown")
    artist = (
        song.get("artists", [{}])[0].get("name", "Unknown") if song.get("artists") else "Unknown"
    )

    console.print()
    log_step(f"Now Playing ({index + 1}/{total})", f"{title} - {artist}")


def log_user_action(action: str, detail: str = ""):
    """Log user interaction"""
    if not _VERBOSE:
        return

    timestamp = time.strftime("%H:%M:%S")
    if detail:
        console.print(
            f"[dim]{timestamp}[/dim]   [magenta]◆[/magenta] [magenta]{action}:[/magenta] {detail}"
        )
        log_to_file(f"{timestamp}   ◆ {action}: {detail}")
    else:
        console.print(f"[dim]{timestamp}[/dim]   [magenta]◆[/magenta] [magenta]{action}[/magenta]")
        log_to_file(f"{timestamp}   ◆ {action}")


def log_dislike_action(song_title: str, song_artist: str, permanent: bool = False):
    """Log dislike action"""
    if not _VERBOSE:
        return

    if permanent:
        log_warning(f"Permanently disliked: {song_title} - {song_artist}")
        log_info("This song will be filtered from future searches and radio playlists")
    else:
        log_info(f"Removed from playlist: {song_title} - {song_artist}")
        log_info("Press 'd' again to permanently dislike")


def log_playlist_add(song_title: str, song_artist: str, playlist_name: str):
    """Log adding song to playlist"""
    if not _VERBOSE:
        return

    log_user_action("Added to playlist", f'"{song_title}" → "{playlist_name}"')


def log_api_call(endpoint: str, params: Dict[str, Any] = None):
    """Log YouTube Music API call"""
    if not _VERBOSE:
        return

    log_info(f"API: {endpoint}")
    if params:
        param_str = ", ".join([f"{k}={v}" for k, v in list(params.items())[:3]])
        log_info(f"Params: {param_str}")


def print_verbose_summary():
    """Print summary when verbose mode is enabled"""
    if not _VERBOSE:
        return

    console.print(
        "\n[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]"
    )
    console.print("[bold green]Verbose logging enabled[/bold green]")
    if _VERBOSE_FILE:
        console.print(f"[green]Logging to file: {_VERBOSE_FILE}[/green]")
    console.print(
        "[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]\n"
    )
