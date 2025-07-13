from ytmusicapi import YTMusic
from rich import print
import subprocess
import time
import sys
import tty
import termios
import os
import argparse
import signal
import select

__version__ = "0.1.0"

# Configuration
SONGS_TO_DISPLAY = 7

def goodbye_message(signum, frame):
    """Handle Ctrl+C gracefully with a goodbye message"""
    print("\n[yellow]👋 Goodbye! Thanks for using YTM CLI! 💩 💩 💩 [/yellow]")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, goodbye_message)

def clear_screen():
    """Clear the terminal screen in a cross-platform way"""
    os.system('cls' if os.name == 'nt' else 'clear')

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def play_music_with_controls(playlist):
    current_song_index = 0
    mpv_process = None

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        while 0 <= current_song_index < len(playlist):
            if mpv_process:
                mpv_process.terminate()
                mpv_process.wait()

            item = playlist[current_song_index]
            video_id = item['videoId']
            
            title = item.get('title', 'Unknown Title')
            if 'artists' in item and item['artists'] and item['artists'][0].get('name'):
                 title = f"{title} - {item['artists'][0]['name']}"

            url = f"https://music.youtube.com/watch?v={video_id}"
            clear_screen()
            print(f"\n[green]▶️ Playing: {title}[/green]")
            print("[cyan]n: next song, b: previous song, q: quit to search[/cyan]")
            
            mpv_process = subprocess.Popen(["mpv", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            while True:
                if mpv_process.poll() is not None:
                    current_song_index += 1
                    break

                rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                if rlist:
                    key = sys.stdin.read(1)
                    if key == 'n':
                        current_song_index += 1
                        break
                    elif key == 'b':
                        if current_song_index > 0:
                            current_song_index -= 1
                        break
                    elif key == 'q':
                        if mpv_process:
                            mpv_process.terminate()
                            mpv_process.wait()
                        # Restore terminal settings before returning
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        return
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if mpv_process:
            mpv_process.terminate()
            mpv_process.wait()


def search_and_play(query=None):
    if query is None:
        query = input("🎵 Search for a song: ")
    else:
        print(f"🎵 Searching for: {query}")
    
    ytmusic = YTMusic()

    results = ytmusic.search(query, filter="songs")
    if not results:
        print("[red]No songs found.[/red]")
        return

    current_selection = 0
    while True:
        clear_screen()
        for i, song in enumerate(results[:SONGS_TO_DISPLAY]):
            title = song['title']
            artist = song['artists'][0]['name']
            if i == current_selection:
                print(f"> [bold green]{i+1}. {title} - {artist}[/bold green]")
            else:
                print(f"  {i+1}. {title} - {artist}")

        key = getch()
        if key == 'j':
            current_selection = (current_selection + 1) % SONGS_TO_DISPLAY
        elif key == 'k':
            current_selection = (current_selection - 1 + SONGS_TO_DISPLAY) % SONGS_TO_DISPLAY
        elif key == '\r': # Enter key
            break
        elif key == 'q':
            return

    song = results[current_selection]
    
    playlist = [song]
    
    print("\n[yellow]🎶 Fetching Radio...[/yellow]")
    try:
        radio = ytmusic.get_watch_playlist(videoId=song['videoId'])
        playlist.extend(radio['tracks'][1:])
    except Exception as e:
        print(f"[red]Error fetching radio: {e}[/red]")


    play_music_with_controls(playlist)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Music CLI")
    parser.add_argument("query", nargs="?", help="Song to search for (optional)")
    args = parser.parse_args()

    search_and_play(args.query)
