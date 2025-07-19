"""MPV player functionality for YTM CLI"""

import subprocess
import time
import sys
import tty
import termios
import os
import select
import json
import socket
import tempfile

from ytm_cli.utils import goodbye_message

from .config import get_mpv_flags, ytmusic


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


def get_and_display_lyrics(video_id, title, socket_path=None):
    """Get and display lyrics for a song"""
    from .ui import display_lyrics_with_curses
    
    try:
        # Use get_watch_playlist to get lyrics browseId (correct method)
        watch_playlist = ytmusic.get_watch_playlist(videoId=video_id)
        
        if watch_playlist and 'lyrics' in watch_playlist and watch_playlist['lyrics']:
            lyrics_data = ytmusic.get_lyrics(watch_playlist['lyrics'])
            if lyrics_data and 'lyrics' in lyrics_data:
                display_lyrics_with_curses(lyrics_data['lyrics'], title, socket_path)
                return True
            else:
                print("No lyrics content found.")
                time.sleep(1)
                return False
        else:
            print("No lyrics available for this song.")
            time.sleep(1)
            return False
    except Exception as e:
        print(f"Error getting lyrics: {e}")
        time.sleep(1)
        return False


def play_music_with_controls(playlist):
    """Play music with keyboard controls"""
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
            
            def cleanup():
                if mpv_process:
                    mpv_process.terminate()
                    mpv_process.wait()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            
            def update_display():
                from .ui import display_player_status
                display_player_status(title, is_paused)
            
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
                        elif key == 'q' or key == '\x03':
                            cleanup()
                            goodbye_message(None, None)
                            return
            
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if mpv_process:
            mpv_process.terminate()
            mpv_process.wait()
        if socket_path and os.path.exists(socket_path):
            os.unlink(socket_path)