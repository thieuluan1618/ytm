"""Main entry point and search functionality for YTM CLI"""

import argparse
from curses import wrapper
from rich import print

from .config import ytmusic, get_songs_to_display
from .ui import selection_ui
from .player import play_music_with_controls
from .utils import setup_signal_handler


def search_and_play(query=None):
    """Search for music and start playback"""
    if query is None:
        query = input("🎵 Search for a song: ")
    else:
        print(f"🎵 Searching for: {query}")
    
    results = ytmusic.search(query, filter="songs")
    if not results:
        print("[red]No songs found.[/red]")
        return

    songs_to_display = get_songs_to_display()
    
    def ui_wrapper(stdscr):
        return selection_ui(stdscr, results, query, songs_to_display)

    selected_index = wrapper(ui_wrapper)
    if selected_index is None:
        return

    song = results[selected_index]
    playlist = [song]

    print("\n[yellow]🎶 Fetching Radio...[/yellow]")
    try:
        radio = ytmusic.get_watch_playlist(videoId=song['videoId'])
        playlist.extend(radio['tracks'][1:])
    except Exception as e:
        print(f"[red]Error fetching radio: {e}[/red]")

    play_music_with_controls(playlist)


def main():
    """Main CLI entry point"""
    setup_signal_handler()
    
    parser = argparse.ArgumentParser(description="YouTube Music CLI 🎧")
    parser.add_argument("query", nargs="?", help="Song to search for (optional)")
    args = parser.parse_args()

    search_and_play(args.query)


if __name__ == "__main__":
    main()