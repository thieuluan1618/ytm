"""Hybrid player for CLI mode with mpv/FFmpeg fallback support"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from typing import Optional

from .config import get_mpv_flags
from .tui.ffmpeg_player import FFmpegPlayerService
from .verbose_logger import log_error, log_info, log_section


class CLIHybridPlayerService:
    """Hybrid player for CLI mode that uses mpv by default, falls back to FFmpeg if needed"""

    def __init__(self):
        self.mpv_process: Optional[subprocess.Popen] = None
        self.ffmpeg_player: Optional[FFmpegPlayerService] = None
        self.player_type: str = "none"
        self.socket_path: Optional[str] = None
        self._initialize_player()

    def _initialize_player(self) -> None:
        """Initialize player with fallback logic"""
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

    def play(self, video_id: str, title: str = "") -> bool:
        """Start playing a song"""
        if not self.is_available():
            log_error("Play attempted but no audio player available")
            print("No audio player available")
            return False

        if self.player_type == "mpv":
            return self._play_mpv(video_id, title)
        elif self.player_type == "ffmpeg" and self.ffmpeg_player:
            return self.ffmpeg_player.play(video_id, title)

        return False

    def _play_mpv(self, video_id: str, title: str = "") -> bool:
        """Play using mpv"""
        try:
            # Clean up previous process if exists
            self.stop()

            # Create socket for IPC
            self.socket_path = tempfile.mktemp(suffix=".sock")

            url = f"https://music.youtube.com/watch?v={video_id}"
            mpv_flags = get_mpv_flags()
            mpv_flags.extend([f"--input-ipc-server={self.socket_path}"])

            log_info(f"Starting MPV playback: {title or video_id}")
            self.mpv_process = subprocess.Popen(
                ["mpv", url] + mpv_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for mpv to create the IPC socket before returning
            for _ in range(20):
                time.sleep(0.1)
                if os.path.exists(self.socket_path):
                    return True
            # Socket not created but process is running
            return self.mpv_process.poll() is None
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

    def is_playing(self) -> bool:
        """Check if music is currently playing.

        For mpv, checks both process state and playback idle status via IPC.
        This prevents false positives when mpv is buffering or loading.
        """
        if self.player_type == "mpv" and self.mpv_process:
            if self.mpv_process.poll() is not None:
                return False
            # Also check if mpv reports idle (finished playing)
            if self.socket_path and os.path.exists(self.socket_path):
                idle = self._get_mpv_property("idle-active")
                if idle is True:
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

    def _send_mpv_command(self, command: dict) -> None:
        """Send a command to mpv via IPC socket"""
        if not self.socket_path:
            return

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            sock.send((json.dumps(command) + "\n").encode())
            sock.close()
        except Exception:
            pass  # Ignore errors if mpv isn't ready yet

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
