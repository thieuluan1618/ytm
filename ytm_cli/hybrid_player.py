"""Hybrid player for CLI mode with mpv/FFmpeg fallback support"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from typing import NamedTuple

from yt_dlp.utils.networking import std_headers
from yt_dlp.version import __version__ as YTDLP_VERSION

from .config import clear_player_pid, get_cookies_browser, get_mpv_flags, save_player_pid
from .ffmpeg_player import FFmpegPlayerService
from .verbose_logger import is_verbose, log_error, log_info, log_section

_NEXT_REQUEST_PROPERTY = "user-data/ytm-cli/next-requested"
_MIN_YTDLP_VERSION = (2026, 8, 19)


def _is_ytdlp_outdated(version: str) -> bool:
    """Return whether yt-dlp predates the minimum reliable playback release."""
    parts = version.split(".")
    if len(parts) < 3:
        return False
    try:
        installed = tuple(int(part) for part in parts[:3])
    except ValueError:
        return False
    return installed < _MIN_YTDLP_VERSION


class ResolvedAudio(NamedTuple):
    """Direct audio URL and the user agent required to request it."""

    url: str
    user_agent: str


def resolve_audio_url(video_id: str) -> ResolvedAudio | None:
    """Pre-resolve audio stream details via yt-dlp.

    Deliberately resolves WITHOUT browser cookies: URLs resolved from a
    logged-in session are rejected with HTTP 403 when mpv later fetches
    them directly (YouTube ties them to PO tokens mpv cannot supply),
    which made every song skip silently. If a video actually requires
    cookies, resolution fails and the caller falls back to letting mpv's
    internal yt-dlp handle it (which passes cookies correctly).
    """
    try:
        cmd = [
            "yt-dlp",
            "-f",
            "bestaudio",
            "--print",
            "%(url)s",
            "--print",
            "%(http_headers)j",
            f"https://music.youtube.com/watch?v={video_id}",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().splitlines()
            for url, raw_headers in zip(lines, lines[1:], strict=False):
                if not url.startswith(("http://", "https://")):
                    continue
                headers = json.loads(raw_headers)
                user_agent = headers.get("User-Agent")
                if isinstance(user_agent, str) and user_agent:
                    return ResolvedAudio(url, user_agent)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


class CLIHybridPlayerService:
    """Hybrid player for CLI mode that uses mpv by default, falls back to FFmpeg if needed"""

    def __init__(self):
        self.mpv_process: subprocess.Popen | None = None
        self.ffmpeg_player: FFmpegPlayerService | None = None
        self.player_type: str = "none"
        self.socket_path: str | None = None
        self._mpv_playback_started = False
        self._initialize_player()

    def _initialize_player(self) -> None:
        """Initialize player with fallback logic"""
        if _is_ytdlp_outdated(YTDLP_VERSION):
            minimum = ".".join(str(part) for part in _MIN_YTDLP_VERSION)
            print(f"⚠ yt-dlp {YTDLP_VERSION} is outdated and may cause songs to skip.")
            print(f"  Run ytm-cli --update to install {minimum} or newer.")

        # Try mpv first
        if shutil.which("mpv"):
            self.player_type = "mpv"
            log_info("MPV player available, using for playback")
            print("✓ Using mpv for playback (high quality, full controls)")
            return

        # Fall back to FFmpeg
        try:
            log_section("Player Initialization", "🎵")
            log_info("MPV not found, attempting FFmpeg fallback...")
            self.ffmpeg_player = FFmpegPlayerService()
            self.player_type = "ffmpeg"
            log_info("FFmpeg player initialized successfully")
            print("✓ Using FFmpeg for playback (fallback mode)")
            return
        except Exception as e:
            log_error(f"FFmpeg initialization failed: {e}")
            print(f"⚠ FFmpeg initialization failed: {e}")

        # No player available
        self.player_type = "none"
        log_error("No audio player available (mpv and FFmpeg both unavailable)")
        print("❌ No audio player available. Install mpv or FFmpeg")

    def is_available(self) -> bool:
        """Check if any player is available"""
        return self.player_type != "none"

    def play(
        self, video_id: str, title: str = "", resolved_audio: ResolvedAudio | None = None
    ) -> bool:
        """Start playing a song, optionally using pre-resolved stream details."""
        if not self.is_available():
            log_error("Play attempted but no audio player available")
            print("No audio player available")
            return False

        if self.player_type == "mpv":
            return self._play_mpv(video_id, title, resolved_audio)
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            return self.ffmpeg_player.play(video_id, title)

        return False

    def _play_mpv(
        self, video_id: str, title: str = "", resolved_audio: ResolvedAudio | None = None
    ) -> bool:
        """Play using mpv"""
        try:
            # Clean up previous process if exists
            self.stop()
            self._mpv_playback_started = False

            # Create socket for IPC
            self.socket_path = tempfile.mktemp(suffix=".sock")

            url = (
                resolved_audio.url
                if resolved_audio
                else f"https://music.youtube.com/watch?v={video_id}"
            )
            mpv_flags = get_mpv_flags()
            mpv_flags.extend(
                [
                    f"--input-ipc-server={self.socket_path}",
                    "--af-append=@vstats:lavfi=[astats=metadata=1:reset=1:length=0.1]",
                ]
            )
            user_agent = resolved_audio.user_agent if resolved_audio else std_headers["User-Agent"]
            mpv_flags.append(f"--user-agent={user_agent}")
            # Pass cookies to mpv's internal yt-dlp when playing unresolved URLs
            if not resolved_audio:
                browser = get_cookies_browser()
                if browser:
                    mpv_flags.append(f"--ytdl-raw-options=cookies-from-browser={browser}")

            log_info(f"Starting MPV playback: {title or video_id}")
            self.mpv_process = subprocess.Popen(
                ["mpv", url] + mpv_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            # Save MPV PID for --terminate
            if self.mpv_process:
                save_player_pid(self.mpv_process.pid)

            # Wait for mpv to create the IPC socket before returning
            for _ in range(30):
                time.sleep(0.1)
                # Check if mpv exited early (e.g., yt-dlp failure)
                if self.mpv_process.poll() is not None:
                    stderr_out = ""
                    if self.mpv_process.stderr:
                        stderr_out = self.mpv_process.stderr.read().decode(errors="replace")
                        self.mpv_process.stderr.close()
                    log_error(
                        f"MPV exited early (code {self.mpv_process.returncode}): {stderr_out[:200]}"
                    )
                    clear_player_pid()
                    self.mpv_process = None
                    return False
                if os.path.exists(self.socket_path):
                    self._install_media_key_bindings()
                    if is_verbose():
                        ao = self._get_mpv_property("current-ao")
                        volume = self._get_mpv_property("volume")
                        mute = self._get_mpv_property("mute")
                        aid = self._get_mpv_property("aid")
                        log_info(
                            f"MPV audio output: ao={ao or 'unknown'}, aid={aid}, "
                            f"volume={volume}, mute={mute}"
                        )
                    # Detach stderr now that startup succeeded (avoid blocking on pipe)
                    if self.mpv_process.stderr:
                        self.mpv_process.stderr.close()
                    return True

            # Socket not created but process is running — close stderr pipe
            if self.mpv_process and self.mpv_process.stderr:
                self.mpv_process.stderr.close()
            return self.mpv_process.poll() is None if self.mpv_process else False
        except Exception as e:
            log_error(f"Failed to start mpv: {e}")
            print(f"Failed to start mpv: {e}")
            return False

    def stop(self) -> None:
        """Stop playback"""
        if self.player_type == "mpv" and self.mpv_process:
            self.mpv_process.terminate()
            self.mpv_process.wait()
            self.mpv_process = None
            if self.socket_path and os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
                self.socket_path = None
            clear_player_pid()
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            self.ffmpeg_player.stop()

    def pause(self) -> None:
        """Pause playback"""
        if self.player_type == "mpv" and self.socket_path:
            self._send_mpv_command({"command": ["set_property", "pause", True]})
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            self.ffmpeg_player.pause()

    def resume(self) -> None:
        """Resume playback"""
        if self.player_type == "mpv" and self.socket_path:
            self._send_mpv_command({"command": ["set_property", "pause", False]})
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            self.ffmpeg_player.resume()

    def consume_next_request(self) -> bool:
        """Return whether mpv's OS media control requested the next CLI track."""
        if self.player_type != "mpv" or not self.socket_path:
            return False

        if not self._get_mpv_property(_NEXT_REQUEST_PROPERTY):
            return False

        self._send_mpv_command({"command": ["set_property", _NEXT_REQUEST_PROPERTY, False]})
        return True

    def is_playing(self) -> bool:
        """Check if music is currently playing.

        MPV can briefly report itself as idle after creating its IPC socket but
        before loading the first file. Only treat idle as end-of-track after MPV
        has reported an active file at least once.
        """
        if self.player_type == "mpv" and self.mpv_process:
            if self.mpv_process.poll() is not None:
                return False
            if self.socket_path and os.path.exists(self.socket_path):
                idle = self._get_mpv_property("idle-active")
                if idle is False:
                    self._mpv_playback_started = True
                elif idle is True and self._mpv_playback_started:
                    return False
            return True
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            return self.ffmpeg_player.is_playing_now()

        return False

    def _get_mpv_property(self, prop: str):
        """Get a property value from mpv via IPC socket."""
        if not self.socket_path:
            return None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            cmd = json.dumps({"command": ["get_property", prop]}) + "\n"
            sock.send(cmd.encode())
            sock.settimeout(0.3)
            data = sock.recv(4096).decode()
            sock.close()
            for line in data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parsed = json.loads(line)
                if "event" not in parsed and parsed.get("error") == "success":
                    return parsed.get("data")
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None

    def _install_media_key_bindings(self) -> bool:
        """Clear mpv's timeline and route Next media keys to the CLI queue."""
        config_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".conf", encoding="utf-8", delete=False
            ) as config:
                config.write(
                    f"NEXT no-osd set pause yes; no-osd set time-pos 0; "
                    f"no-osd set {_NEXT_REQUEST_PROPERTY} yes\n"
                    f"XF86_NEXT no-osd set pause yes; no-osd set time-pos 0; "
                    f"no-osd set {_NEXT_REQUEST_PROPERTY} yes\n"
                )
                config_path = config.name

            return self._send_mpv_command(
                {"command": ["load-input-conf", config_path]},
                expect_response=True,
            )
        except OSError:
            return False
        finally:
            if config_path and os.path.exists(config_path):
                os.unlink(config_path)

    def _send_mpv_command(self, command: dict, expect_response: bool = False) -> bool:
        """Send a command to mpv via IPC socket."""
        if not self.socket_path:
            return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send((json.dumps(command) + "\n").encode())
            if expect_response:
                sock.settimeout(0.3)
                response = sock.recv(4096).decode()
                sock.close()
                for line in response.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    parsed = json.loads(line)
                    if "event" not in parsed:
                        return parsed.get("error") == "success"
                return False
            sock.close()
            return True
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return False

    def get_player_info(self) -> dict:
        """Get information about the current player"""
        return {
            "type": self.player_type,
            "available": self.is_available(),
            "playing": self.is_playing() if self.is_available() else False,
        }

    def cleanup(self) -> None:
        """Clean up player resources"""
        self.stop()
        if self.player_type == "ffmpeg" and self.ffmpeg_player:
            self.ffmpeg_player.cleanup()
            self.ffmpeg_player = None
