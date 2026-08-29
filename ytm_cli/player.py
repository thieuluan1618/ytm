"""MPV player functionality for YTM CLI"""

import curses
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty

from ytm_cli.utils import goodbye_message

from .config import get_ytmusic
from .dislikes import dislike_manager
from .playlists import playlist_manager
from .ui import display_lyrics_with_curses


class CavaVisualizer:
    """Manages a cava subprocess for audio visualization."""

    def __init__(self, num_bars=30):
        self.process = None
        self.bars = []
        self.num_bars = num_bars
        self._config_path = None

    def start(self):
        """Start cava in raw ASCII output mode."""
        if not shutil.which("cava"):
            return False

        self._config_path = tempfile.mktemp(suffix=".cava.conf")
        with open(self._config_path, "w") as f:
            f.write(
                f"[general]\nbars = {self.num_bars}\nframerate = 15\n\n"
                f"[output]\nmethod = raw\nraw_target = /dev/stdout\n"
                f"data_format = ascii\nascii_max_range = 8\n"
            )

        try:
            self.process = subprocess.Popen(
                ["cava", "-p", self._config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            # Set stdout to non-blocking
            import fcntl

            fd = self.process.stdout.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            return True
        except OSError:
            return False

    def read_bars(self):
        """Read latest bar values from cava. Returns list of ints (0-8)."""
        if not self.process or self.process.poll() is not None:
            return self.bars

        try:
            # Read all available data, use the last complete line
            data = self.process.stdout.read(4096)
            if data:
                lines = data.decode("ascii", errors="ignore").strip().split("\n")
                last_line = lines[-1]
                values = [int(v) for v in last_line.split(";") if v.strip()]
                if values:
                    self.bars = values
        except (BlockingIOError, ValueError):
            pass
        return self.bars

    def stop(self):
        """Stop cava subprocess and clean up."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        if self._config_path:
            try:
                os.unlink(self._config_path)
            except OSError:
                pass
            self._config_path = None
        self.bars = []


def _mpv_ipc(socket_path, command, expect_response=False):
    """Send a command to mpv via IPC socket and optionally read a response."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.send((json.dumps(command) + "\n").encode())
        if expect_response:
            sock.settimeout(0.5)
            buf = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                # Process each line — skip event messages, return command response
                for line in buf.split(b"\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if "event" in data:
                        continue
                    if data.get("error") == "success":
                        sock.close()
                        return data.get("data")
                    sock.close()
                    return None
            sock.close()
            return None
        sock.close()
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TimeoutError):
        return None


def send_mpv_command(socket_path, command):
    """Send a command to mpv via IPC socket"""
    _mpv_ipc(socket_path, command)


def get_mpv_time_position(socket_path):
    """Get current playback position from MPV"""
    result = _mpv_ipc(socket_path, {"command": ["get_property", "time-pos"]}, expect_response=True)
    return result if result is not None else 0


def get_mpv_pause_state(socket_path):
    """Get current pause state from MPV"""
    result = _mpv_ipc(socket_path, {"command": ["get_property", "pause"]}, expect_response=True)
    return result if result is not None else False


def get_mpv_duration(socket_path):
    """Get total duration of current track from MPV"""
    result = _mpv_ipc(socket_path, {"command": ["get_property", "duration"]}, expect_response=True)
    return result if result is not None else 0


def get_mpv_resolved_url(socket_path):
    """Return the direct media URL mpv resolved via yt-dlp, or None.

    `stream-open-filename` exposes the post-resolution URL ffmpeg can fetch.
    """
    result = _mpv_ipc(
        socket_path,
        {"command": ["get_property", "stream-open-filename"]},
        expect_response=True,
    )
    if isinstance(result, str) and result.startswith(("http://", "https://")):
        return result
    return None


def get_mpv_audio_levels(socket_path):
    """Get normalized audio levels from mpv's astats filter.

    Returns dict {peak, rms, left, right} with floats 0.0-1.0, or None.
    Each value derives from a per-frame astats reading (length=0.1s window)
    so bars track real MP3 dynamics — no microphone, no FFT.
    """
    result = _mpv_ipc(
        socket_path,
        {"command": ["get_property", "af-metadata/vstats"]},
        expect_response=True,
    )
    if not isinstance(result, dict):
        return None

    def _norm(key, floor_db=-60.0):
        raw = result.get(key)
        if raw is None:
            return None
        try:
            db = float(raw)
        except (ValueError, TypeError):
            return None
        if db != db or db <= floor_db:  # NaN or -inf / silence
            return 0.0
        if db >= 0.0:
            return 1.0
        return (db - floor_db) / (-floor_db)

    return {
        "peak": _norm("lavfi.astats.Overall.Peak_level"),
        "rms": _norm("lavfi.astats.Overall.RMS_level"),
        "left": _norm("lavfi.astats.1.RMS_level"),
        "right": _norm("lavfi.astats.2.RMS_level"),
    }


def get_mpv_audio_level(socket_path):
    """Back-compat: overall RMS as float 0..1, or None."""
    levels = get_mpv_audio_levels(socket_path)
    return levels.get("rms") if levels else None


def add_song_to_playlist_interactive(song_data):
    """Select a playlist and return its name on success.

    Returns ``None`` when cancelled and ``False`` when persistence fails.
    """
    import curses
    from curses import wrapper

    def playlist_selection_ui(stdscr, song_title):
        """Curses UI for playlist selection"""

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
            return None

        if selected_playlist == "CREATE_NEW":
            # Create new playlist
            print("\nCreate new playlist:")
            playlist_name = input("Playlist name: ").strip()
            if not playlist_name:
                # Generate unique default name with timestamp and counter
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = f"My Playlist #{timestamp}"
                playlist_name = base_name

                # Check if this name already exists and add counter if needed
                existing_names = playlist_manager.get_playlist_names()
                if playlist_name in existing_names:
                    counter = 1
                    while f"{base_name}_{counter}" in existing_names:
                        counter += 1
                    playlist_name = f"{base_name}_{counter}"

                print(f"[cyan]Using default name: {playlist_name}[/cyan]")

            # Create the playlist
            if playlist_manager.create_playlist(playlist_name, "", notify=False):
                selected_playlist = playlist_name
            else:
                return False

        # Add song to selected playlist
        if playlist_manager.add_song_to_playlist(selected_playlist, song_data, notify=False):
            return selected_playlist
        return False

    finally:
        # Restore raw terminal mode for player controls
        tty.setraw(sys.stdin.fileno())


def get_and_display_lyrics(video_id, title, socket_path=None, is_playing_func=None):
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
        artist_name = None
        if " - " in title:
            artist_name = title.split(" - ", 1)[1]
            song_item["artists"] = [{"name": artist_name}]

        song_title = title.split(" - ")[0] if " - " in title else title

        timestamped_lyrics = get_timestamped_lyrics(song_item)

        if timestamped_lyrics and (
            timestamped_lyrics.get("synced_lyrics") or timestamped_lyrics.get("plain_lyrics")
        ):
            display_lyrics_with_curses(
                timestamped_lyrics,
                song_title,
                artist_name,
                socket_path,
                get_mpv_time_position,
                is_playing_func,
            )
            return True

        # Fallback to YouTube Music lyrics if timestamped lyrics unavailable
        print("📡 Trying YouTube Music lyrics...")
        time.sleep(0.5)

        # Use get_watch_playlist to get lyrics browseId (correct method)
        ytmusic = get_ytmusic()
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
                    fallback_lyrics,
                    song_title,
                    artist_name,
                    socket_path,
                    get_mpv_time_position,
                    is_playing_func,
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


def play_music_with_controls_curses(playlist, playlist_name=None, demo=False, prefetched_url_thread=None):
    """Play music with keyboard controls using curses-based UI

    Args:
        playlist: List of songs to play
        playlist_name: Name of user playlist (if playing from a user playlist)
        demo: When True, use the demo player + synthetic spectrum (no audio,
            no network) so screenshot tooling can capture deterministic frames.
        prefetched_url_thread: Tuple of (thread, result_list) for async stream resolution.
    """
    from .verbose_logger import log_info, log_section

    log_section("Playback Starting", "🎵")
    log_info(f"Total tracks in queue: {len(playlist)}")
    if playlist_name:
        log_info(f"Playing from user playlist: {playlist_name}")

    if demo:
        from .demo import DemoPlayer

        player = DemoPlayer()
    else:
        from .hybrid_player import CLIHybridPlayerService

        player = CLIHybridPlayerService()
    if not player.is_available():
        print("❌ No audio player available. Install mpv or FFmpeg")
        return

    if not sys.stdin.isatty():
        _play_non_interactive(player, playlist)
        return

    quit_pressed = False

    def _curses_main(stdscr):
        nonlocal quit_pressed
        from .ui import draw_player, init_player_colors, push_wave_sample, reset_wave_history

        init_player_colors()
        if demo:
            from .demo import DemoSpectrum

            spectrum = DemoSpectrum(n_bands=24)
        else:
            from .spectrum import SpectrumAnalyzer

            spectrum = SpectrumAnalyzer(n_bands=24) if SpectrumAnalyzer.available() else None
        curses.curs_set(0)
        stdscr.timeout(200)

        current_song_index = 0
        is_paused = False
        frame = 0
        toast_msg = None
        toast_detail = None
        toast_expire = 0

        # Pre-resolved stream details keyed by video ID
        prefetch_cache = {}
        prefetch_lock = threading.Lock()
        _initial_url_thread = None

        # Track the caller's prefetch thread (already running in parallel since song selection)
        if prefetched_url_thread and playlist:
            _initial_url_thread = prefetched_url_thread  # (thread, result_list)

        def _prefetch_audio(vid: str):
            """Resolve audio stream details in the background and cache them."""
            if demo:
                return
            from .hybrid_player import resolve_audio_url

            resolved_audio = resolve_audio_url(vid)
            with prefetch_lock:
                prefetch_cache[vid] = resolved_audio

        def _get_cached_audio(vid: str):
            nonlocal _initial_url_thread
            # Check if the initial prefetch thread has finished
            if _initial_url_thread and playlist:
                audio_thread, audio_result = _initial_url_thread
                if not audio_thread.is_alive():
                    if audio_result[0]:
                        with prefetch_lock:
                            prefetch_cache[playlist[0]["videoId"]] = audio_result[0]
                    _initial_url_thread = None
            with prefetch_lock:
                return prefetch_cache.get(vid)

        def fire(msg, detail=None, duration=1.8):
            nonlocal toast_detail, toast_expire, toast_msg
            toast_msg = msg
            toast_detail = detail
            toast_expire = time.time() + duration

        def dislike_and_skip(song, title, artist_name):
            nonlocal current_song_index
            if not dislike_manager.dislike_song(song, notify=False):
                fire("Could not dislike track", "Playback will continue", duration=3)
                return False

            fire(
                f"Disliked · {title} · {artist_name}",
                "Hidden from future searches and radio playlists",
                duration=3.5,
            )
            player.stop()
            current_song_index += 1
            return True

        try:
            while 0 <= current_song_index < len(playlist):
                reset_wave_history()
                if spectrum is not None:
                    spectrum.stop()
                spectrum_started = False
                item = playlist[current_song_index]
                video_id = item["videoId"]

                song_title = item.get("title", "Unknown Title")
                artist = "Unknown Artist"
                if "artists" in item and item["artists"] and item["artists"][0].get("name"):
                    artist = item["artists"][0]["name"]
                display_title = (
                    f"{song_title} - {artist}" if artist != "Unknown Artist" else song_title
                )

                track_num = current_song_index + 1

                def queue_context(current_index):
                    """Return live queue details as the background radio fetch grows it."""
                    next_index = current_index + 1
                    if next_index >= len(playlist):
                        return len(playlist), None, None
                    next_item = playlist[next_index]
                    next_artists = next_item.get("artists") or []
                    next_artist = (
                        next_artists[0].get("name", "Unknown Artist")
                        if next_artists
                        else "Unknown Artist"
                    )
                    return len(playlist), next_item.get("title", "Unknown Title"), next_artist

                # Prefetch next song's URL while this one loads/plays
                next_idx = current_song_index + 1
                if next_idx < len(playlist) and not demo:
                    next_vid = playlist[next_idx]["videoId"]
                    if _get_cached_audio(next_vid) is None and next_vid not in prefetch_cache:
                        threading.Thread(
                            target=_prefetch_audio, args=(next_vid,), daemon=True
                        ).start()

                # Start playback in background so the UI keeps animating.
                # Wait briefly for prefetch to resolve (animating meanwhile),
                # then start mpv with whatever URL we have.
                play_result = [None]  # None = pending, True/False = done
                play_started = False
                if not toast_msg or time.time() >= toast_expire:
                    fire("Loading...")

                while play_result[0] is None:
                    # Once prefetch resolves (or after a short wait), kick off mpv
                    if not play_started:
                        resolved_audio = _get_cached_audio(video_id)
                        if resolved_audio is not None or frame > 5:
                            # Either resolved the stream or waited ~1s — start mpv
                            def _start_play(
                                vid=video_id,
                                title=display_title,
                                audio=resolved_audio,
                                _res=play_result,
                            ):
                                if demo:
                                    _res[0] = player.play(vid, title)
                                else:
                                    _res[0] = player.play(vid, title, resolved_audio=audio)

                            threading.Thread(target=_start_play, daemon=True).start()
                            play_started = True

                    track_total, next_title, next_artist = queue_context(current_song_index)
                    draw_player(
                        stdscr,
                        song_title,
                        artist,
                        is_paused,
                        track_num,
                        track_total,
                        None,
                        None,
                        frame,
                        toast_msg,
                        toast_expire,
                        next_title=next_title,
                        next_artist=next_artist,
                        toast_detail=toast_detail,
                    )
                    frame += 1
                    key = stdscr.getch()
                    if key == ord("q") or key == 3:
                        quit_pressed = True
                        return
                    if key == ord("n"):
                        current_song_index += 1
                        if play_started:
                            time.sleep(0.1)
                            if play_result[0] is True:
                                player.stop()
                        fire("Next →")
                        break

                if play_result[0] is None:
                    # broke out via 'n'
                    continue

                if not play_result[0]:
                    fire(f"Failed: {song_title}")
                    current_song_index += 1
                    continue

                is_paused = False
                if toast_msg == "Loading...":
                    toast_msg = None
                    toast_detail = None

                lyrics_just_viewed = False

                while True:
                    if player.player_type == "mpv" and player.consume_next_request():
                        player.stop()
                        current_song_index += 1
                        fire("Next →")
                        break
                    elif player.is_playing():
                        # Reset the post-lyrics guard once the player confirms it's still alive.
                        lyrics_just_viewed = False
                    elif lyrics_just_viewed:
                        # Don't auto-advance immediately after returning from the lyrics view;
                        # is_playing() can briefly report False during curses re-init.
                        lyrics_just_viewed = False
                    else:
                        current_song_index += 1
                        break

                    elapsed = duration = audio_levels = None
                    if demo:
                        elapsed = (time.time() - player._start_time) if player._playing else 0
                        duration = player._duration
                        if spectrum is not None and not spectrum_started:
                            spectrum_started = spectrum.start("demo")
                    elif player.player_type == "mpv" and player.socket_path:
                        elapsed = get_mpv_time_position(player.socket_path)
                        duration = get_mpv_duration(player.socket_path)
                        audio_levels = get_mpv_audio_levels(player.socket_path)

                        if spectrum is not None and not spectrum_started:
                            resolved = get_mpv_resolved_url(player.socket_path)
                            if resolved:
                                spectrum_started = spectrum.start(resolved)

                    if audio_levels and not is_paused:
                        push_wave_sample(audio_levels)

                    bands = spectrum.get_bands() if spectrum is not None else None

                    track_total, next_title, next_artist = queue_context(current_song_index)
                    draw_player(
                        stdscr,
                        song_title,
                        artist,
                        is_paused,
                        track_num,
                        track_total,
                        elapsed,
                        duration,
                        frame,
                        toast_msg,
                        toast_expire,
                        audio_levels=audio_levels,
                        bands=bands,
                        next_title=next_title,
                        next_artist=next_artist,
                        toast_detail=toast_detail,
                    )
                    frame += 1

                    key = stdscr.getch()
                    if key == -1 or key == curses.KEY_RESIZE:
                        continue

                    if key == ord(" "):
                        is_paused = not is_paused
                        if is_paused:
                            player.pause()
                        else:
                            player.resume()
                    elif key == ord("n"):
                        player.stop()
                        current_song_index += 1
                        fire("Next →")
                        break
                    elif key == ord("b"):
                        player.stop()
                        if current_song_index > 0:
                            current_song_index -= 1
                        fire("← Prev")
                        break
                    elif key == ord("l"):
                        socket_path = None
                        if player.player_type == "mpv" and player.socket_path:
                            socket_path = player.socket_path

                        def lyrics_playback_active():
                            if player.player_type == "mpv" and player.consume_next_request():
                                player.stop()
                                return False
                            return player.is_playing()

                        curses.endwin()
                        get_and_display_lyrics(
                            video_id,
                            display_title,
                            socket_path,
                            is_playing_func=lyrics_playback_active,
                        )
                        stdscr.clear()
                        stdscr.refresh()
                        curses.curs_set(0)
                        stdscr.timeout(200)
                        lyrics_just_viewed = True
                    elif key == ord("a"):
                        curses.endwin()
                        add_result = add_song_to_playlist_interactive(item)
                        stdscr.clear()
                        stdscr.refresh()
                        curses.curs_set(0)
                        stdscr.timeout(200)
                        if add_result:
                            fire(
                                f"Added · {song_title} · {artist}",
                                f"Saved to playlist · {add_result}",
                                duration=3.5,
                            )
                        elif add_result is False:
                            fire(
                                f"Could not add · {song_title}",
                                "The track may already be saved in that playlist",
                                duration=3.5,
                            )
                        else:
                            fire("Add cancelled")
                    elif key == ord("d"):
                        vid = item.get("videoId")
                        stitle = item.get("title", "Unknown")

                        if playlist_name and vid:
                            if dislike_manager.is_disliked(vid):
                                fire("Already disliked")
                            elif playlist_manager.remove_song_from_playlist_by_id(
                                playlist_name, vid
                            ):
                                fire(
                                    "Removed from playlist",
                                    "Press D again to hide it from search and radio",
                                    duration=3.5,
                                )
                            else:
                                if dislike_and_skip(item, stitle, artist):
                                    break
                        else:
                            if dislike_and_skip(item, stitle, artist):
                                break
                    elif key == ord("q") or key == 3:
                        quit_pressed = True
                        return
        finally:
            if spectrum is not None:
                spectrum.stop()

    try:
        curses.wrapper(_curses_main)
    finally:
        player.cleanup()

    if quit_pressed:
        goodbye_message()


def _play_non_interactive(player, playlist):
    """Play through playlist without keyboard interaction (non-TTY fallback)."""
    from .ui import display_player_status

    try:
        for i, item in enumerate(playlist):
            video_id = item["videoId"]
            title = item.get("title", "Unknown Title")
            if "artists" in item and item["artists"] and item["artists"][0].get("name"):
                title = f"{title} - {item['artists'][0]['name']}"

            display_player_status(
                title,
                False,
                track_index=i + 1,
                track_total=len(playlist),
            )

            if not player.play(video_id, title):
                continue

            while True:
                if player.player_type == "mpv" and player.consume_next_request():
                    player.stop()
                    break
                if not player.is_playing():
                    break
                time.sleep(0.5)
    finally:
        player.cleanup()


def play_music_with_controls_rich(playlist, playlist_name=None, demo=False, prefetched_url_thread=None):
    """Play music with keyboard controls using rich-based UI.

    Args:
        playlist: List of songs to play
        playlist_name: Name of user playlist (if playing from a user playlist)
        demo: When True, use the demo player + synthetic spectrum
        prefetched_url_thread: Tuple of (thread, result_list) for async stream resolution
    """
    from .rich_ui import play_with_rich_ui
    from .verbose_logger import log_info, log_section

    log_section("Playback Starting (Rich UI)", "🎵")
    log_info(f"Total tracks in queue: {len(playlist)}")
    if playlist_name:
        log_info(f"Playing from user playlist: {playlist_name}")

    if demo:
        from .demo import DemoPlayer
        player = DemoPlayer()
    else:
        from .hybrid_player import CLIHybridPlayerService
        player = CLIHybridPlayerService()

    if not player.is_available():
        print("❌ No audio player available. Install mpv or FFmpeg")
        return

    if not sys.stdin.isatty():
        _play_non_interactive(player, playlist)
        return

    def get_elapsed():
        if player.player_type == "mpv" and player.socket_path:
            return get_mpv_time_position(player.socket_path)
        return None

    def get_duration():
        if player.player_type == "mpv" and player.socket_path:
            return get_mpv_duration(player.socket_path)
        return None

    def on_pause():
        if player.is_playing():
            player.pause()
        else:
            player.resume()

    def on_lyrics(song):
        video_id = song.get("videoId")
        title = song.get("title", "Unknown")
        if video_id:
            get_and_display_lyrics(video_id, title, player.socket_path, player.is_playing)

    def on_add_playlist(song):
        return add_song_to_playlist_interactive(song)

    def on_dislike(song):
        dislike_manager.dislike_song(song, notify=False)

    try:
        play_with_rich_ui(
            player=player,
            playlist=playlist,
            playlist_name=playlist_name,
            get_elapsed=get_elapsed,
            get_duration=get_duration,
            on_pause=on_pause,
            on_lyrics=on_lyrics,
            on_add_playlist=on_add_playlist,
            on_dislike=on_dislike,
        )
    finally:
        player.cleanup()


def play_music_with_controls(playlist, playlist_name=None, demo=False, prefetched_url_thread=None):
    """Play music with keyboard controls.

    Routes to either curses or rich UI based on config.

    Args:
        playlist: List of songs to play
        playlist_name: Name of user playlist (if playing from a user playlist)
        demo: When True, use the demo player
        prefetched_url_thread: Tuple of (thread, result_list) for async stream resolution
    """
    from .config import use_rich_ui

    if use_rich_ui():
        return play_music_with_controls_rich(playlist, playlist_name, demo, prefetched_url_thread)
    else:
        return play_music_with_controls_curses(playlist, playlist_name, demo, prefetched_url_thread)
