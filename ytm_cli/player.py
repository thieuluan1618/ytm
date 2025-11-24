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
from .verbose_logger import (
    log_mpv_start,
    log_mpv_stop,
)
from .verbose_logger import (
    set_verbose as set_verbose_logger,
)


def set_verbose(enabled, log_file=None):
    """Set verbose mode and optional log file"""
    set_verbose_logger(enabled, log_file)


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
        sock.send(
            json.dumps({"command": ["get_property", "time-pos"]}).encode() + b"\n"
        )
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
        selected_playlist = wrapper(
            lambda stdscr: playlist_selection_ui(stdscr, song_title)
        )

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
            timestamped_lyrics.get("synced_lyrics")
            or timestamped_lyrics.get("plain_lyrics")
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
    """Play music with keyboard controls using hybrid player

    Args:
        playlist: List of songs to play
        playlist_name: Name of user playlist (if playing from a user playlist)
    """
    from .hybrid_player import CLIHybridPlayerService
    from .verbose_logger import log_info, log_section

    log_section("Playback Starting", "🎵")
    log_info(f"Total tracks in queue: {len(playlist)}")
    if playlist_name:
        log_info(f"Playing from user playlist: {playlist_name}")

    # Initialize hybrid player
    player = CLIHybridPlayerService()
    if not player.is_available():
        print("❌ No audio player available. Install mpv or pygame")
        return

    current_song_index = 0
    is_paused = False
    last_pause_check = 0

    # Check if we're in a TTY environment
    is_tty = sys.stdin.isatty()
    
    if is_tty:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
        except termios.error as e:
            print(f"Warning: Could not set raw terminal mode: {e}")
            is_tty = False

    try:
        while 0 <= current_song_index < len(playlist):
            from .verbose_logger import (
                log_info as vlog_info,
            )
            from .verbose_logger import (
                log_song_change as vlog_song_change,
            )
            from .verbose_logger import (
                log_user_action as vlog_user_action,
            )

            item = playlist[current_song_index]
            video_id = item["videoId"]

            title = item.get("title", "Unknown Title")
            artist = "Unknown Artist"

            if "artists" in item and item["artists"] and item["artists"][0].get("name"):
                artist = item["artists"][0]["name"]
                title = f"{title} - {artist}"

            # Log song change
            vlog_song_change(current_song_index, len(playlist), item)

            def cleanup():
                player.cleanup()
                if is_tty:
                    try:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    except termios.error:
                        pass  # Ignore errors during cleanup

            def update_display(current_title, current_paused):
                from .ui import display_player_status

                display_player_status(current_title, current_paused)

            update_display(title, is_paused)

            # Start playback with hybrid player
            if not player.play(video_id, title):
                print(f"Failed to play: {title}")
                current_song_index += 1
                continue

            # Log player start
            player_info = player.get_player_info()
            vlog_info(f"Started playback with {player_info['type']} player")
            is_paused = False
            last_pause_check = 0  # Reset pause check timer for new song

            while True:
                if not player.is_playing():
                    # Song finished or error occurred
                    current_song_index += 1
                    break

                # Update display if pause state changed
                current_time = time.time()
                if current_time - last_pause_check > 0.5:
                    # For mpv, we could check pause state via IPC if needed
                    # For now, we'll track it locally
                    last_pause_check = current_time

                # Handle keyboard input only if in TTY
                if is_tty:
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.2)
                    if rlist:
                        key = sys.stdin.read(1)
                        if key == " ":  # Space bar for play/pause
                            is_paused = not is_paused
                            if is_paused:
                                player.pause()
                            else:
                                player.resume()
                            update_display(title, is_paused)
                        elif key == "n":
                            player.stop()
                            current_song_index += 1
                            break
                        elif key == "b":
                            if current_song_index > 0:
                                player.stop()
                                current_song_index -= 1
                            break
                        elif key == "l":
                            # Show lyrics - for mpv we need socket path
                            socket_path = None
                            if player.player_type == "mpv" and player.socket_path:
                                socket_path = player.socket_path
                            get_and_display_lyrics(video_id, title, socket_path)
                            update_display(title, is_paused)
                        elif key == "a":
                            # Add current song to playlist
                            add_song_to_playlist_interactive(item)
                            update_display(title, is_paused)
                        elif key == "d":
                            # Smart two-step dislike system
                            video_id = item.get("videoId")
                            song_title = item.get("title", "Unknown")

                            if playlist_name and video_id:
                                # Playing from a user playlist - two-step process
                                from .playlists import playlist_manager

                                # Check if song is already globally disliked
                                if dislike_manager.is_disliked(video_id):
                                    print(
                                        f"⏭️  '{song_title}' already disliked globally, skipping..."
                                    )
                                else:
                                    # Try to remove from playlist first
                                    if playlist_manager.remove_song_from_playlist_by_id(
                                        playlist_name, video_id
                                    ):
                                        print(
                                            f"📝 Removed '{song_title}' from playlist '{playlist_name}'"
                                        )
                                        print(
                                            "   💡 Press 'd' again to add to global dislikes"
                                        )
                                        time.sleep(
                                            1.5
                                        )  # Give user time to read and potentially press 'd' again
                                    else:
                                        # Song not in playlist anymore or couldn't remove, add to global dislikes
                                        dislike_manager.dislike_song(item)
                                        print(f"👎 Disliked '{song_title}' globally")
                                        current_song_index += 1
                                        time.sleep(0.8)  # Brief pause to show message
                                        break
                            else:
                                # Playing from search/radio - direct dislike
                                dislike_manager.dislike_song(item)
                                song_title = item.get("title", "Unknown")
                                print(f"👎 Disliked '{song_title}' globally")
                                current_song_index += 1
                                time.sleep(0.8)  # Brief pause to show message
                                break
                        elif key == "q" or key == "\x03":
                            cleanup()
                            goodbye_message()
                            return
                else:
                    # Non-TTY mode: just play through the playlist without interaction
                    time.sleep(0.5)  # Check playback status every 0.5 seconds

    finally:
        if is_tty:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except termios.error:
                pass  # Ignore errors during cleanup
        player.cleanup()
