"""MPV player functionality for YTM CLI"""

import json
import os
import select
import socket
import subprocess
import sys
import tempfile
import termios
import time
import tty

from ytm_cli.utils import goodbye_message

from .config import get_mpv_flags, ytmusic
from .dislikes import dislike_manager
from .playlists import playlist_manager
from .ui import display_lyrics_with_curses


def send_mpv_command(socket_path, command):
    """Send a command to mpv via IPC socket"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send((json.dumps(command) + "\n").encode())
        sock.close()
    except (OSError, json.JSONEncodeError):
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


def get_mpv_pause_state(socket_path):
    """Get current pause state from MPV"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send(json.dumps({"command": ["get_property", "pause"]}).encode() + b"\n")
        sock.settimeout(0.1)
        response = sock.recv(1024).decode()
        sock.close()

        response_data = json.loads(response)
        if response_data.get("error") == "success":
            return response_data.get("data", False)
    except Exception:
        pass
    return False


def add_song_to_playlist_interactive(song_data):
    """Interactive playlist selection and song addition during playback"""
    import sys
    import termios
    import tty
    from curses import wrapper

    def playlist_selection_ui(stdscr, song_title):
        """Curses UI for playlist selection"""
        import curses

        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Get existing playlists
        playlists = playlist_manager.get_playlist_names()

        # If only one playlist exists, auto-select it (keep music simple!)
        if len(playlists) == 1:
            return playlists[0]

        # Menu options
        options = ["Create new playlist"]
        options.extend(playlists)

        selected_index = 0

        while True:
            stdscr.clear()

            # Title
            title = f"Add '{song_title}' to playlist:"
            stdscr.addstr(0, 0, title[: width - 1], curses.A_BOLD)
            stdscr.addstr(1, 0, "=" * min(len(title), width - 1))

            # Instructions
            stdscr.addstr(3, 0, "↑↓ or j/k: Navigate | Enter: Select | q: Cancel")

            # Menu options
            start_row = 5
            for i, option in enumerate(options):
                if i >= height - start_row - 2:
                    break

                row = start_row + i
                prefix = "→ " if i == selected_index else "  "
                text = f"{prefix}{option}"

                if i == selected_index:
                    stdscr.addstr(row, 0, text[: width - 1], curses.A_REVERSE)
                else:
                    stdscr.addstr(row, 0, text[: width - 1])

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()

            if key in [ord("q"), ord("Q"), 27]:  # q or ESC
                return None
            elif key in [ord("j"), curses.KEY_DOWN]:
                selected_index = (selected_index + 1) % len(options)
            elif key in [ord("k"), curses.KEY_UP]:
                selected_index = (selected_index - 1) % len(options)
            elif key in [10, 13, curses.KEY_ENTER]:  # Enter
                if selected_index == 0:  # Create new playlist
                    return "CREATE_NEW"
                else:
                    return options[selected_index]

    # Save terminal state
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        # Reset terminal to normal mode for curses
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        # Run playlist selection UI
        song_title = song_data.get("title", "Unknown")
        selected_playlist = wrapper(lambda stdscr: playlist_selection_ui(stdscr, song_title))

        if selected_playlist is None:
            # User cancelled
            print("\nCancelled adding song to playlist.")
            time.sleep(1)
            return False

        if selected_playlist == "CREATE_NEW":
            # Create new playlist
            print("\nCreate new playlist:")
            playlist_name = input("Playlist name: ").strip()
            if not playlist_name:
                print("Cancelled - no name provided.")
                time.sleep(1)
                return False

            description = input("Description (optional): ").strip()

            # Create the playlist
            if playlist_manager.create_playlist(playlist_name, description):
                selected_playlist = playlist_name
            else:
                print("Failed to create playlist.")
                time.sleep(1)
                return False

        # Add song to selected playlist
        success = playlist_manager.add_song_to_playlist(selected_playlist, song_data)
        time.sleep(1.5)  # Give user time to see the message
        return success

    finally:
        # Restore raw terminal mode for player controls
        tty.setraw(sys.stdin.fileno())


def get_and_display_lyrics(video_id, title, socket_path=None):
    """Get and display lyrics for a song"""
    from .lyrics_service import get_timestamped_lyrics

    try:
        # First try to get timestamped lyrics from LRCLIB
        # We need to construct a song item to match the expected format
        song_item = {
            "title": title.split(" - ")[0] if " - " in title else title,
            "videoId": video_id,
        }

        # Extract artist from title if present
        if " - " in title:
            artist_name = title.split(" - ", 1)[1]
            song_item["artists"] = [{"name": artist_name}]

        timestamped_lyrics = get_timestamped_lyrics(song_item)

        if timestamped_lyrics and (
            timestamped_lyrics.get("synced_lyrics") or timestamped_lyrics.get("plain_lyrics")
        ):
            display_lyrics_with_curses(
                timestamped_lyrics, title, socket_path, get_mpv_time_position
            )
            return True

        # Fallback to YouTube Music lyrics if timestamped lyrics unavailable
        print("📡 Trying YouTube Music lyrics...")
        time.sleep(0.5)

        # Use get_watch_playlist to get lyrics browseId (correct method)
        watch_playlist = ytmusic.get_watch_playlist(videoId=video_id)

        if watch_playlist and "lyrics" in watch_playlist and watch_playlist["lyrics"]:
            lyrics_data = ytmusic.get_lyrics(watch_playlist["lyrics"])
            if lyrics_data and "lyrics" in lyrics_data:
                # Format as plain text with source info for consistency
                fallback_lyrics = {
                    "plain_lyrics": lyrics_data["lyrics"],
                    "source": "YouTube Music",
                }
                display_lyrics_with_curses(
                    fallback_lyrics, title, socket_path, get_mpv_time_position
                )
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


def play_music_with_controls(playlist, playlist_name=None):
    """Play music with keyboard controls

    Args:
        playlist: List of songs to play
        playlist_name: Name of user playlist (if playing from a user playlist)
    """
    current_song_index = 0
    mpv_process = None
    socket_path = None
    is_paused = False
    last_pause_check = 0

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
            video_id = item["videoId"]

            title = item.get("title", "Unknown Title")

            if "artists" in item and item["artists"] and item["artists"][0].get("name"):
                title = f"{title} - {item['artists'][0]['name']}"

            url = f"https://music.youtube.com/watch?v={video_id}"

            # Create a temporary socket for mpv IPC
            socket_path = tempfile.mktemp(suffix=".sock")

            def cleanup(mpv_proc=mpv_process):
                if mpv_proc:
                    mpv_proc.terminate()
                    mpv_proc.wait()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            def update_display(song_title, is_paused=is_paused):
                from .ui import display_player_status

                display_player_status(song_title, is_paused)

            update_display(title)

            mpv_flags = get_mpv_flags()
            mpv_flags.extend([f"--input-ipc-server={socket_path}"])

            mpv_process = subprocess.Popen(
                ["mpv", url] + mpv_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            is_paused = False
            last_pause_check = 0  # Reset pause check timer for new song

            # Give mpv a moment to start and create the socket
            time.sleep(0.1)

            while True:
                if mpv_process.poll() is not None:
                    current_song_index += 1
                    break

                # Check if mpv pause state has changed (sync with player UI)
                # Only check every 0.5 seconds to avoid excessive IPC calls
                current_time = time.time()
                if current_time - last_pause_check > 0.5:
                    mpv_pause_state = get_mpv_pause_state(socket_path)
                    if mpv_pause_state != is_paused:
                        is_paused = mpv_pause_state
                        update_display(title)
                    last_pause_check = current_time

                rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                if rlist:
                    key = sys.stdin.read(1)
                    if key == " ":  # Space bar for play/pause
                        is_paused = not is_paused
                        send_mpv_command(socket_path, {"command": ["cycle", "pause"]})
                        update_display(title)
                    elif key == "n":
                        current_song_index += 1
                        break
                    elif key == "b":
                        if current_song_index > 0:
                            current_song_index -= 1
                        break
                    elif key == "l":
                        # Show lyrics
                        get_and_display_lyrics(video_id, title, socket_path)
                        update_display(title)
                    elif key == "a":
                        # Add current song to playlist
                        add_song_to_playlist_interactive(item)
                        update_display(title)
                    elif key == "d":
                        # Smart two-step dislike system
                        video_id = item.get("videoId")
                        song_title = item.get("title", "Unknown")

                        if playlist_name and video_id:
                            # Playing from a user playlist - two-step process
                            from .playlists import playlist_manager

                            # Check if song is already globally disliked
                            if dislike_manager.is_disliked(video_id):
                                print(f"⏭️  '{song_title}' already disliked globally, skipping...")
                            else:
                                # Try to remove from playlist first
                                if playlist_manager.remove_song_from_playlist_by_id(
                                    playlist_name, video_id
                                ):
                                    print(
                                        f"📝 Removed '{song_title}' from playlist '{playlist_name}'"
                                    )
                                    print("   💡 Press 'd' again to add to global dislikes")
                                    time.sleep(
                                        1.5
                                    )  # Give user time to read and potentially press 'd' again
                                else:
                                    # Song not in playlist anymore or couldn't remove, add to global dislikes
                                    dislike_manager.dislike_song(item)
                                    print(f"👎 Added '{song_title}' to global dislikes")
                        else:
                            # Not from a user playlist, directly add to global dislikes
                            dislike_manager.dislike_song(item)
                            print(f"👎 Disliked '{song_title}'")

                        current_song_index += 1
                        time.sleep(0.8)  # Brief pause to show message
                        break
                    elif key == "q" or key == "\x03":
                        cleanup()
                        goodbye_message()
                        return

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if mpv_process:
            mpv_process.terminate()
            mpv_process.wait()
        if socket_path and os.path.exists(socket_path):
            os.unlink(socket_path)
