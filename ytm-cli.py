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
import configparser
import curses
from curses import wrapper
import json
import socket
import tempfile

__version__ = "0.1.0"

config = configparser.ConfigParser()
config.read('config.ini')
songs_to_display = int(config.get('general', 'songs_to_display', fallback='5'))

def get_mpv_flags():
    if 'mpv' in config and 'flags' in config['mpv']:
        return config['mpv']['flags'].split()
    return []

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

def send_mpv_command(socket_path, command):
    """Send a command to mpv via IPC socket"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send((json.dumps(command) + "\n").encode())
        sock.close()
    except Exception:
        pass  # Ignore errors if mpv isn't ready yet

def play_music_with_controls(playlist):
    current_song_index = 0
    mpv_process = None
    socket_path = None
    is_paused = False

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        while 0 <= current_song_index < len(playlist):
            if mpv_process:
                mpv_process.terminate()
                mpv_process.wait()
            
            if socket_path and os.path.exists(socket_path):
                os.unlink(socket_path)

            item = playlist[current_song_index]
            video_id = item['videoId']
            
            title = item.get('title', 'Unknown Title')
            if 'artists' in item and item['artists'] and item['artists'][0].get('name'):
                 title = f"{title} - {item['artists'][0]['name']}"

            url = f"https://music.youtube.com/watch?v={video_id}"
            
            # Create a temporary socket for mpv IPC
            socket_path = tempfile.mktemp(suffix='.sock')
            
            def update_display():
                clear_screen()
                status = "⏸️ Paused" if is_paused else "▶️ Playing"
                print(f"\n[green]{status}: {title}[/green]")
                print("[cyan]space: play/pause, n: next song, b: previous song, q: quit to search[/cyan]")
            
            update_display()
            
            mpv_flags = get_mpv_flags()
            mpv_flags.extend([f"--input-ipc-server={socket_path}"])

            mpv_process = subprocess.Popen(["mpv", url] + mpv_flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            is_paused = False

            # Give mpv a moment to start and create the socket
            time.sleep(0.1)

            while True:
                if mpv_process.poll() is not None:
                    current_song_index += 1
                    break

                rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                if rlist:
                    key = sys.stdin.read(1)
                    if key == ' ':  # Space bar for play/pause
                        is_paused = not is_paused
                        send_mpv_command(socket_path, {"command": ["cycle", "pause"]})
                        update_display()
                    elif key == 'n':
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
        if socket_path and os.path.exists(socket_path):
            os.unlink(socket_path)


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

    config = configparser.ConfigParser()
    config.read('config.ini')
    songs_to_display = int(config.get('general', 'songs_to_display', fallback='10'))

    def selection_ui(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        
        # Define color pair 1: yellow text, default background
        curses.init_pair(1, curses.COLOR_YELLOW, -1)
        YELLOW = curses.color_pair(1)

        current_selection = 0

        while True:
            stdscr.erase()
            stdscr.addstr(0, 0, f"🎵 Search Results for: {query}\n\n")

            for i, song in enumerate(results[:songs_to_display]):
                title = song['title']
                artist = song['artists'][0]['name']
                line = f"[{i+1}] {title} - {artist}"

                if i == current_selection:
                    stdscr.addstr(i + 2, 0, f"> {line}", YELLOW)
                else:
                    stdscr.addstr(i + 2, 0, f"  {line}")

            stdscr.refresh()
            key = stdscr.getch()

            if key in (curses.KEY_DOWN, ord('j')):
                current_selection = (current_selection + 1) % songs_to_display
            elif key in (curses.KEY_UP, ord('k')):
                current_selection = (current_selection - 1 + songs_to_display) % songs_to_display
            elif key in (ord('\n'), 10, 13):
                return current_selection
            elif key == ord('q'):
                return None
            elif ord('1') <= key <= ord(str(min(9, songs_to_display))):
                return key - ord('1')


    selected_index = wrapper(selection_ui)
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



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Music CLI")
    parser.add_argument("query", nargs="?", help="Song to search for (optional)")
    args = parser.parse_args()

    search_and_play(args.query)
