"""Background player service for TUI"""

import subprocess
import tempfile
import os
from typing import Optional

from ..config import get_mpv_flags


class TUIPlayerService:
    """Manages mpv playback for the TUI in the background"""

    def __init__(self):
        self.mpv_process: Optional[subprocess.Popen] = None
        self.socket_path: Optional[str] = None
        self.current_video_id: Optional[str] = None

    def play(self, video_id: str, title: str = "") -> bool:
        """Start playing a song in the background

        Args:
            video_id: YouTube video ID
            title: Song title for logging

        Returns:
            True if playback started successfully
        """
        try:
            # Stop any existing playback
            self.stop()

            # Create socket for IPC
            self.socket_path = tempfile.mktemp(suffix=".sock")
            self.current_video_id = video_id

            # Build mpv command
            url = f"https://music.youtube.com/watch?v={video_id}"
            mpv_flags = get_mpv_flags()
            mpv_flags.extend([f"--input-ipc-server={self.socket_path}"])

            # Start mpv process
            self.mpv_process = subprocess.Popen(
                ["mpv", url] + mpv_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return True

        except Exception as e:
            print(f"Error starting playback: {e}")
            return False

    def stop(self) -> None:
        """Stop current playback"""
        if self.mpv_process:
            try:
                self.mpv_process.terminate()
                self.mpv_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.mpv_process.kill()
                self.mpv_process.wait()

            self.mpv_process = None

        # Clean up socket
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception:
                pass
            self.socket_path = None

    def is_playing(self) -> bool:
        """Check if music is currently playing"""
        if self.mpv_process is None:
            return False
        return self.mpv_process.poll() is None

    def pause(self) -> None:
        """Pause playback"""
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                import json
                import socket

                sock = socket.socket(socket.AF_UNIX)
                sock.connect(self.socket_path)
                sock.sendall(
                    json.dumps({"command": ["cycle", "pause"]}).encode() + b"\n"
                )
                sock.close()
            except Exception:
                pass

    def resume(self) -> None:
        """Resume playback"""
        self.pause()  # Cycle pause to resume
