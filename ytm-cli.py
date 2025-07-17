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

__version__ = "0.2.0"

config = configparser.ConfigParser()
config.read('config.ini')
songs_to_display = int(config.get('general', 'songs_to_display', fallback='5'))
ytmusic = YTMusic()

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

def get_mpv_time_position(socket_path):
    """Get current playback position from MPV"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send(json.dumps({"command": ["get_property", "time-pos"]}).encode() + b"\n")
        sock.settimeout(0.1)
        response = sock.recv(1024).decode()
        sock.close()
        
        response_data = json.loads(response)
        if response_data.get("error") == "success":
            return response_data.get("data", 0)
    except Exception:
        pass
    return 0

def display_lyrics_with_curses(lyrics_text, title, socket_path=None):
    """Display lyrics using curses with live highlighting"""
    def lyrics_ui(stdscr):
        curses.curs_set(0)  # Hide cursor
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Header
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Lyrics text
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Footer/instructions
        curses.init_pair(4, curses.COLOR_GREEN, -1)   # Highlight
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Current line highlight
        
        HEADER_COLOR = curses.color_pair(1)
        TEXT_COLOR = curses.color_pair(2)
        FOOTER_COLOR = curses.color_pair(3)
        HIGHLIGHT_COLOR = curses.color_pair(4)
        CURRENT_LINE_COLOR = curses.color_pair(5)
        
        # Prepare lyrics lines
        lines = [line.strip() for line in lyrics_text.split('\n')]
        max_y, max_x = stdscr.getmaxyx()
        
        # Wrap long lines to fit terminal width
        wrapped_lines = []
        for line in lines:
            if len(line) <= max_x - 4:  # Leave margin
                wrapped_lines.append(line)
            else:
                # Simple word wrapping
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= max_x - 4:
                        current_line += " " + word if current_line else word
                    else:
                        wrapped_lines.append(current_line)
                        current_line = word
                if current_line:
                    wrapped_lines.append(current_line)
        
        lines = wrapped_lines
        scroll_pos = 0
        content_height = max_y - 4  # Reserve space for header and footer
        start_time = time.time()
        
        # Estimate line timing (rough approximation)
        non_empty_lines = [i for i, line in enumerate(lines) if line.strip()]
        line_duration = 3.0  # Assume 3 seconds per line on average
        
        while True:
            stdscr.erase()
            
            # Calculate current highlighted line based on playback time
            current_highlighted_line = -1
            if socket_path:
                current_time = get_mpv_time_position(socket_path)
                if current_time > 0 and non_empty_lines:
                    # Estimate which line should be highlighted
                    estimated_line_index = int(current_time / line_duration)
                    if estimated_line_index < len(non_empty_lines):
                        current_highlighted_line = non_empty_lines[estimated_line_index]
            
            # Auto-scroll to follow highlighted line
            if current_highlighted_line >= 0:
                if current_highlighted_line < scroll_pos:
                    scroll_pos = max(0, current_highlighted_line - 2)
                elif current_highlighted_line >= scroll_pos + content_height:
                    scroll_pos = min(current_highlighted_line - content_height + 3, len(lines) - content_height)
                    if scroll_pos < 0:
                        scroll_pos = 0
            
            # Header
            header_text = f"🎵 {title}"
            border = "═" * (max_x - 2)
            
            stdscr.addstr(0, 0, border[:max_x-1], HEADER_COLOR)
            if len(header_text) < max_x - 1:
                stdscr.addstr(1, (max_x - len(header_text)) // 2, header_text, HEADER_COLOR)
            else:
                stdscr.addstr(1, 0, header_text[:max_x-1], HEADER_COLOR)
            stdscr.addstr(2, 0, border[:max_x-1], HEADER_COLOR)
            
            # Display lyrics content
            for i in range(content_height):
                line_idx = scroll_pos + i
                if line_idx < len(lines):
                    line = lines[line_idx]
                    if line:
                        # Highlight the current line
                        if line_idx == current_highlighted_line:
                            stdscr.addstr(3 + i, 2, f"♪ {line[:max_x-5]}", CURRENT_LINE_COLOR)
                        else:
                            stdscr.addstr(3 + i, 2, line[:max_x-3], TEXT_COLOR)
                    # Empty lines create natural spacing
            
            # Footer with instructions
            footer_y = max_y - 1
            total_lines = len(lines)
            
            if total_lines > content_height:
                # Show scroll info with time position
                progress = f"[{scroll_pos + 1}-{min(scroll_pos + content_height, total_lines)}/{total_lines}]"
                time_info = ""
                if socket_path:
                    current_time = get_mpv_time_position(socket_path)
                    time_info = f" | {int(current_time//60)}:{int(current_time%60):02d}"
                instructions = f"j/k: scroll | q: back{time_info} | {progress}"
            else:
                instructions = "q: back to player"
            
            if len(instructions) < max_x - 1:
                stdscr.addstr(footer_y, 0, instructions[:max_x-1], FOOTER_COLOR)
            
            stdscr.refresh()
            
            # Handle input with timeout for live updates
            stdscr.timeout(500)  # 500ms timeout
            key = stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('j') or key == curses.KEY_DOWN:
                if scroll_pos + content_height < len(lines):
                    scroll_pos += 1
            elif key == ord('k') or key == curses.KEY_UP:
                if scroll_pos > 0:
                    scroll_pos -= 1
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(scroll_pos + content_height, len(lines) - content_height)
                if scroll_pos < 0:
                    scroll_pos = 0
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(scroll_pos - content_height, 0)
            elif key == curses.KEY_HOME:  # Home - go to top
                scroll_pos = 0
            elif key == curses.KEY_END:  # End - go to bottom
                scroll_pos = max(len(lines) - content_height, 0)
    
    return wrapper(lyrics_ui)

def get_and_display_lyrics(video_id, title, socket_path=None):
    """Get and display lyrics for a song"""
    try:
        # Use get_watch_playlist to get lyrics browseId (correct method)
        watch_playlist = ytmusic.get_watch_playlist(videoId=video_id)
        
        if watch_playlist and 'lyrics' in watch_playlist and watch_playlist['lyrics']:
            lyrics_data = ytmusic.get_lyrics(watch_playlist['lyrics'])
            if lyrics_data and 'lyrics' in lyrics_data:
                display_lyrics_with_curses(lyrics_data['lyrics'], title, socket_path)
                return True
            else:
                print("[red]No lyrics content found.[/red]")
                time.sleep(1)
                return False
        else:
            print("[red]No lyrics available for this song.[/red]")
            time.sleep(1)
            return False
    except Exception as e:
        print(f"[red]Error getting lyrics: {e}[/red]")
        time.sleep(1)
        return False

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
                print("[cyan]space: play/pause, n: next song, b: previous song, l: lyrics, q: quit to search[/cyan]")
            
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
                    elif key == 'l':
                        # Show lyrics
                        get_and_display_lyrics(video_id, title, socket_path)
                        update_display()
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
