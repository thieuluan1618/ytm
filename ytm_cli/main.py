"""Main entry point and search functionality for YTM CLI"""

import argparse
import curses
import sys
from curses import wrapper

from rich import print

from .config import get_songs_to_display, ytmusic
from .dislikes import dislike_manager
from .player import play_music_with_controls
from .playlists import playlist_manager
from .ui import selection_ui
from .utils import setup_signal_handler
from .verbose_logger import (
    log_api_call,
    log_playlist_composition,
    log_radio_generation,
    log_search_results,
    log_section,
    log_step,
    log_success,
    log_warning,
    print_verbose_summary,
    set_verbose,
)

_VERBOSE = False
_VERBOSE_FILE = None


def search_and_play(query=None, auto_select=None):
    """Search for music and start playback

    Args:
        query: Search query string
        auto_select: If set, auto-select this song number (1-based) without UI
    """
    if query is None:
        query = input("🎵 Search for a song: ")
    else:
        print(f"🎵 Searching for: {query}")

    log_section("Music Search", "🔍")
    log_step("Searching YouTube Music", query)
    log_api_call("ytmusic.search", {"query": query, "filter": "songs"})

    try:
        results = ytmusic.search(query, filter="songs")
    except Exception as e:
        print(f"[red]Network error while searching: {e}[/red]")
        print("[yellow]Please check your internet connection and try again.[/yellow]")
        return

    if not results:
        print("[red]No songs found.[/red]")
        return

    log_success(f"Found {len(results)} results")

    # Filter out disliked songs
    original_count = len(results)
    results = dislike_manager.filter_disliked_songs(results)
    filtered_count = original_count - len(results)

    if filtered_count > 0:
        log_warning(f"Filtered out {filtered_count} disliked song(s)")

    if not results:
        print("[red]No songs found after filtering dislikes.[/red]")
        return

    # Log search results in verbose mode
    log_search_results(query, results, filtered_count)

    songs_to_display = get_songs_to_display()

    # Non-interactive mode: auto-select specified song
    if auto_select is not None:
        log_step("Auto-selecting song", f"#{auto_select}")
        selected_index = auto_select - 1  # Convert to 0-based index

        if selected_index < 0 or selected_index >= len(results):
            print(f"[red]Invalid selection {auto_select}. Valid range: 1-{len(results)}[/red]")
            return

        song = results[selected_index]
        title = song["title"]
        artist = song["artists"][0]["name"] if song.get("artists") else "Unknown Artist"
        print(f"[green]✓ Selected:[/green] {title} - {artist}")
        log_success(f"Selected: {title} - {artist}")

    else:
        # Interactive mode: use curses UI
        def ui_wrapper(stdscr):
            return selection_ui(stdscr, results, query, songs_to_display)

        try:
            selected_index = wrapper(ui_wrapper)
        except curses.error as e:
            print(f"[red]Terminal error: {e}[/red]")
            print(
                "[yellow]Try resizing your terminal or using a different terminal emulator.[/yellow]"
            )
            # Fallback to simple numbered selection
            print(f"\n[cyan]Search Results for: {query}[/cyan]")
            for i, song in enumerate(results[:songs_to_display]):
                title = song["title"]
                artist = song["artists"][0]["name"]
                print(f"[{i + 1}] {title} - {artist}")

            try:
                choice = input("\nEnter song number (or 'q' to quit): ").strip()
                if choice.lower() == "q":
                    return
                selected_index = int(choice) - 1
                if selected_index < 0 or selected_index >= len(results[:songs_to_display]):
                    print("[red]Invalid selection.[/red]")
                    return
            except (ValueError, KeyboardInterrupt):
                return

        if selected_index is None:
            return

    song = results[selected_index]
    playlist = [song]

    # Fetch radio in background so the first song starts immediately
    import threading

    def fetch_radio():
        log_step("Fetching radio playlist", f"videoId: {song['videoId']}")
        log_api_call("ytmusic.get_watch_playlist", {"videoId": song["videoId"]})
        try:
            radio = ytmusic.get_watch_playlist(videoId=song["videoId"])
            radio_tracks = radio["tracks"][1:]  # Skip first track (the selected song)

            log_success(f"Radio returned {len(radio_tracks)} tracks")

            # Filter out disliked songs from radio
            original_radio_count = len(radio_tracks)
            filtered_radio = dislike_manager.filter_disliked_songs(radio_tracks)
            filtered_radio_count = original_radio_count - len(filtered_radio)

            # Log radio generation details
            log_radio_generation(song["videoId"], original_radio_count, filtered_radio_count)

            playlist.extend(filtered_radio)
            log_success(f"Final playlist ready: {len(playlist)} tracks")

            # Log playlist composition
            log_playlist_composition(playlist, 0)

        except Exception as e:
            log_warning(f"Error fetching radio: {e}")
            log_warning(f"Exception details: {str(e)}")

    radio_thread = threading.Thread(target=fetch_radio, daemon=True)
    radio_thread.start()

    play_music_with_controls(playlist)


# Playlist Commands


def playlist_list_command():
    """List all playlists"""
    playlists = playlist_manager.list_playlists()

    if not playlists:
        print("[yellow]No playlists found.[/yellow]")
        print("Create your first playlist: [cyan]python -m ytm_cli playlist create[/cyan]")
        return

    print(f"\n[cyan]📁 Local Playlists ({len(playlists)} found)[/cyan]")
    print("=" * 60)

    for i, playlist in enumerate(playlists, 1):
        name = playlist["name"]
        song_count = playlist["song_count"]
        description = playlist["description"]
        created_at = playlist["created_at"][:10] if playlist["created_at"] else "Unknown"

        print(f"\n[{i}] [yellow]{name}[/yellow]")
        print(f"    Songs: {song_count}")
        if description:
            print(f"    Description: {description}")
        print(f"    Created: {created_at}")

    print("\n[green]💡 Commands:[/green]")
    print("• [cyan]python -m ytm_cli playlist show <name>[/cyan] - View playlist songs")
    print("• [cyan]python -m ytm_cli playlist play <name>[/cyan] - Play a playlist")
    print("• [cyan]python -m ytm_cli playlist delete <name>[/cyan] - Delete a playlist")


def playlist_create_command(name, description=""):
    """Create a new playlist"""
    if not name:
        name = input("Enter playlist name: ").strip()
        if not name:
            print("[red]Playlist name is required[/red]")
            return

    if not description:
        description = input("Enter description (optional): ").strip()

    playlist_manager.create_playlist(name, description)


def playlist_show_command(name):
    """Show songs in a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # If only one playlist exists, auto-select it (keep music simple!)
        if len(playlists) == 1:
            name = playlists[0]
            print(f"[cyan]Showing playlist: {name}[/cyan]")
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    playlist = playlist_manager.get_playlist(name)
    if not playlist:
        print(f"[red]Playlist '{name}' not found[/red]")
        return

    songs = playlist.get("songs", [])

    print(f"\n[cyan]🎵 Playlist: {playlist['name']}[/cyan]")
    if playlist.get("description"):
        print(f"Description: {playlist['description']}")
    print(f"Songs: {len(songs)}")
    print("=" * 60)

    if not songs:
        print("[yellow]No songs in this playlist[/yellow]")
        print("Add songs by searching and pressing 'a' during selection!")
        return

    for i, song in enumerate(songs, 1):
        title = song.get("title", "Unknown")
        artist = song.get("artist", "Unknown Artist")
        duration = song.get("duration", "")
        added_at = song.get("added_at", "")[:10] if song.get("added_at") else ""

        print(f"[{i:2d}] {title} - {artist}")
        if duration:
            print(f"     Duration: {duration}")
        if added_at:
            print(f"     Added: {added_at}")
        print()


def playlist_play_command(name):
    """Play a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # If only one playlist exists, auto-select it (keep music simple!)
        if len(playlists) == 1:
            name = playlists[0]
            print(f"[cyan]Playing playlist: {name}[/cyan]")
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    playlist = playlist_manager.get_playlist(name)
    if not playlist:
        print(f"[red]Playlist '{name}' not found[/red]")
        return

    songs = playlist.get("songs", [])
    if not songs:
        print(f"[yellow]Playlist '{name}' is empty[/yellow]")
        return

    print(f"[green]🎵 Playing playlist: {playlist['name']} ({len(songs)} songs)[/green]")

    # Convert playlist songs to format expected by player
    playable_songs = []
    for song in songs:
        if song.get("videoId"):
            # Create a song object compatible with ytmusicapi format
            playable_song = {
                "title": song.get("title", "Unknown"),
                "artists": [{"name": song.get("artist", "Unknown Artist")}],
                "videoId": song["videoId"],
                "duration_seconds": song.get("duration", ""),
                "album": {"name": song.get("album", "")} if song.get("album") else None,
            }
            playable_songs.append(playable_song)

    # Filter out disliked songs
    playable_songs = dislike_manager.filter_disliked_songs(playable_songs)

    if not playable_songs:
        print("[red]No playable songs found in playlist after filtering dislikes[/red]")
        return

    # Start playback with playlist context
    play_music_with_controls(playable_songs, playlist_name=name)


def playlist_delete_command(name):
    """Delete a playlist"""
    if not name:
        # List available playlists for selection
        playlists = playlist_manager.get_playlist_names()
        if not playlists:
            print("[red]No playlists found[/red]")
            return

        # For deletion, still show selection even with one playlist (safety)
        # but make it clearer if there's only one option
        if len(playlists) == 1:
            print(f"[cyan]Only playlist available: {playlists[0]}[/cyan]")
            name = playlists[0]
        else:
            print("[cyan]Available playlists:[/cyan]")
            for i, playlist_name in enumerate(playlists, 1):
                print(f"[{i}] {playlist_name}")

            try:
                choice = input("\nSelect playlist number or name to delete: ").strip()
                if choice.isdigit():
                    index = int(choice) - 1
                    if 0 <= index < len(playlists):
                        name = playlists[index]
                    else:
                        print("[red]Invalid selection[/red]")
                        return
                else:
                    name = choice
            except (ValueError, KeyboardInterrupt):
                return

    # Confirm deletion
    confirm = input(f"Delete playlist '{name}'? (y/N): ").strip().lower()
    if confirm != "y":
        print("Deletion cancelled")
        return

    playlist_manager.delete_playlist(name)


def llm_create_playlist_command(llm_client, prompt, num_songs=15, auto_play=False, verbose=False):
    """Create a playlist using AI-generated song suggestions"""
    print(f"[cyan]Asking AI to create a playlist: {prompt}[/cyan]")

    response = llm_client.generate_playlist(prompt, num_songs=num_songs, verbose=verbose)
    if not response or not response.songs:
        print("[red]Failed to generate playlist songs[/red]")
        return

    playlist_name = response.query
    print(f"[green]Playlist name: {playlist_name}[/green]")
    print(f"[cyan]Searching YouTube Music for {len(response.songs)} songs...[/cyan]")

    # Create the playlist
    if not playlist_manager.create_playlist(playlist_name, f"AI-generated: {prompt}"):
        return

    # Search each song on YTMusic and add to playlist
    found_count = 0
    for i, song_suggestion in enumerate(response.songs, 1):
        title = song_suggestion.get("title", "")
        artist = song_suggestion.get("artist", "")
        search_query = f"{title} {artist}"

        try:
            results = ytmusic.search(search_query, filter="songs", limit=1)
            if results:
                song = results[0]
                song_title = song.get("title", "Unknown")
                song_artist = song["artists"][0]["name"] if song.get("artists") else "Unknown"
                playlist_manager.add_song_to_playlist(playlist_name, song)
                found_count += 1
                print(f"  [{i}/{len(response.songs)}] {song_title} - {song_artist}")
            else:
                print(f"  [{i}/{len(response.songs)}] Not found: {title} - {artist}")
        except Exception as e:
            print(f"  [{i}/{len(response.songs)}] Error: {title} - {e}")

    print(f"\n[green]Playlist '{playlist_name}' created with {found_count} songs[/green]")

    if auto_play and found_count > 0:
        playlist_play_command(playlist_name)


def main():
    """Main CLI entry point"""
    global _VERBOSE
    setup_signal_handler()

    # Handle backward compatibility first by checking command line arguments
    # But we need to check for flags first
    if (
        len(sys.argv) >= 2
        and not sys.argv[1].startswith("-")
        and sys.argv[1] not in ["search", "playlist", "llm"]
        and "--verbose" not in sys.argv
        and "--select" not in sys.argv
    ):
        # This is likely a song query, handle it directly (backward compatible mode)
        search_and_play(sys.argv[1])
        return

    # Allow `llm "prompt"` as shortcut for `llm ask "prompt"`
    if len(sys.argv) >= 3 and sys.argv[1] == "llm" and sys.argv[2] not in ("ask", "playlist"):
        sys.argv.insert(2, "ask")

    parser = argparse.ArgumentParser(
        description="YouTube Music CLI 🎧 - Search, play, and organize music from YouTube Music",
        epilog="""
Examples:
  %(prog)s "bohemian rhapsody"                    Search and play music
  %(prog)s "phung khanh linh" --select 1          Auto-select first result
  %(prog)s "beatles" --select 2 --verbose         Auto-select with detailed logging
  %(prog)s playlist list                          List all local playlists
  %(prog)s playlist create "Rock Hits"            Create a new playlist
  %(prog)s llm "play upbeat pop songs"            Use AI to find and play music

During song selection:
  • Enter: Play selected song with radio
  • a: Add song to playlist
  • q: Quit to search
  • ↑↓ or j/k: Navigate

During music playback:
  • ⏯️ space: Play/pause
  • ⏭️ n: Next song, ⏮️ b: Previous song
  • 📜 l: Show lyrics, ➕ a: Add to playlist, 👎 d: Dislike (playlist: remove first, then global)
  • 🚪 q: Quit to search
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options (available for all commands)
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logging",
    )

    # Create subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands: search, playlist, llm",
        description="Main commands for the YouTube Music CLI: search, playlist, llm",
    )

    # Search command (explicit)
    search_parser = subparsers.add_parser(
        "search",
        help="Search and play music",
        description="Search YouTube Music and play songs with radio playlists",
    )
    search_parser.add_argument(
        "search_query", nargs="?", help="Song, artist, or album to search for"
    )
    search_parser.add_argument(
        "--select",
        "-s",
        type=int,
        metavar="N",
        help="Auto-select song number N (1-based, non-interactive mode)",
    )
    search_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logging",
    )
    search_parser.add_argument(
        "--log-file",
        metavar="FILE",
        help="Write verbose logs to FILE (requires --verbose)",
    )

    # Playlist commands
    playlist_parser = subparsers.add_parser(
        "playlist",
        help="Local playlist management",
        description='Create and manage local playlists. Add songs during search by pressing "a".',
    )
    playlist_subparsers = playlist_parser.add_subparsers(
        dest="playlist_command", help="Playlist operations"
    )

    # LLM commands
    llm_parser = subparsers.add_parser(
        "llm",
        help="AI-powered music assistant",
        description="Use AI to search, recommend and play music based on natural language requests",
    )
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command", help="LLM operations")

    # llm ask (default behavior)
    llm_ask_parser = llm_subparsers.add_parser("ask", help="Ask AI for music recommendations")
    llm_ask_parser.add_argument(
        "prompt", help="Natural language request for music (e.g. 'play upbeat pop songs')"
    )
    llm_ask_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    # llm playlist - AI-generated playlist
    llm_playlist_parser = llm_subparsers.add_parser(
        "playlist", help="Create a playlist using AI suggestions"
    )
    llm_playlist_parser.add_argument(
        "prompt", help="Describe the playlist (e.g. 'chill lo-fi beats for studying')"
    )
    llm_playlist_parser.add_argument(
        "--songs", "-n", type=int, default=15, help="Number of songs (default: 15)"
    )
    llm_playlist_parser.add_argument(
        "--play", "-p", action="store_true", help="Start playing after creation"
    )
    llm_playlist_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    playlist_subparsers.add_parser(
        "list",
        help="List all local playlists",
        description="Show all created playlists with song counts and metadata",
    )

    create_parser = playlist_subparsers.add_parser(
        "create",
        help="Create a new playlist",
        description="Create a new local playlist with optional description",
    )
    create_parser.add_argument("name", nargs="?", help="Playlist name (prompted if not provided)")
    create_parser.add_argument("-d", "--description", help="Optional playlist description")

    show_parser = playlist_subparsers.add_parser(
        "show",
        help="Show songs in a playlist",
        description="Display all songs in a playlist with details",
    )
    show_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    play_parser = playlist_subparsers.add_parser(
        "play",
        help="Play a playlist",
        description="Start playback of all songs in a playlist",
    )
    play_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    delete_parser = playlist_subparsers.add_parser(
        "delete",
        help="Delete a playlist",
        description="Permanently delete a playlist and all its songs",
    )
    delete_parser.add_argument(
        "name", nargs="?", help="Playlist name (select from list if not provided)"
    )

    args = parser.parse_args()

    # Set verbose mode globally
    global _VERBOSE, _VERBOSE_FILE
    _VERBOSE = getattr(args, "verbose", False)
    _VERBOSE_FILE = getattr(args, "log_file", None)

    # Initialize verbose logger
    set_verbose(_VERBOSE, _VERBOSE_FILE)

    # Initialize log file if specified
    if _VERBOSE_FILE and _VERBOSE:
        try:
            import time

            with open(_VERBOSE_FILE, "w") as f:
                f.write("=== YTM CLI Verbose Log ===\n")
                f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
        except Exception as e:
            print(f"[red]Could not create log file: {e}[/red]")

    # Show verbose mode banner
    if _VERBOSE:
        print_verbose_summary()

    if args.command == "playlist":
        if args.playlist_command == "list":
            playlist_list_command()
        elif args.playlist_command == "create":
            playlist_create_command(args.name, args.description or "")
        elif args.playlist_command == "show":
            playlist_show_command(args.name)
        elif args.playlist_command == "play":
            playlist_play_command(args.name)
        elif args.playlist_command == "delete":
            playlist_delete_command(args.name)
        else:
            print("Available playlist commands: list, create, show, play, delete")
    elif args.command == "llm":
        from .llm_client import LLMClient

        llm_client = LLMClient()

        if args.llm_command == "playlist":
            llm_create_playlist_command(
                llm_client,
                args.prompt,
                args.songs,
                getattr(args, "play", False),
                getattr(args, "verbose", False),
            )
        elif args.llm_command == "ask" or (args.llm_command is None and args.prompt):
            response = llm_client.generate(args.prompt, verbose=getattr(args, "verbose", False))

            if not response:
                print("[red]Failed to process LLM request[/red]")
                return

            if response.action == "search":
                search_and_play(response.query, auto_select=response.parameters.get("limit", 1))
            elif response.action == "playlist":
                playlist_play_command(response.query)
            else:
                print(f"[yellow]Unsupported LLM action: {response.action}[/yellow]")
                print(f"[cyan]Try:[/cyan] {response.query}")
                search_and_play(response.query, auto_select=1)
        else:
            print("Available llm commands: ask, playlist")
    elif args.command == "search":
        auto_select = getattr(args, "select", None)
        search_and_play(args.search_query, auto_select=auto_select)
    else:
        # Default behavior: if no command specified, prompt for search
        search_and_play()


if __name__ == "__main__":
    main()
