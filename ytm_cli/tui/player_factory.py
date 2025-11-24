"""Player factory that provides hybrid mpv/FFmpeg support"""

import shutil
from typing import Union, Optional

from .player_service import TUIPlayerService
from .ffmpeg_player import FFmpegPlayerService


class HybridPlayerService:
    """Hybrid player that uses mpv by default, falls back to FFmpeg if needed"""

    def __init__(self):
        self.player: Union[TUIPlayerService, FFmpegPlayerService, None] = None
        self.player_type: str = "none"
        self._initialize_player()

    def _initialize_player(self) -> None:
        """Initialize player with fallback logic"""
        # Try mpv first
        if shutil.which("mpv"):
            try:
                self.player = TUIPlayerService()
                self.player_type = "mpv"
                print("✓ Using mpv for playback (high quality, full controls)")
                return
            except Exception as e:
                print(f"⚠ mpv initialization failed: {e}")

        # Fall back to FFmpeg
        try:
            self.player = FFmpegPlayerService()
            self.player_type = "ffmpeg"
            print("✓ Using FFmpeg for playback (fallback mode)")
            return
        except Exception as e:
            print(f"⚠ FFmpeg initialization failed: {e}")

        # No player available
        self.player = None
        self.player_type = "none"
        print("❌ No audio player available. Install mpv or FFmpeg")

    def is_available(self) -> bool:
        """Check if any player is available"""
        return self.player is not None

    def play(self, video_id: str, title: str = "") -> bool:
        """Start playing a song"""
        if self.player is None:
            print("No audio player available")
            return False

        return self.player.play(video_id, title)

    def stop(self) -> None:
        """Stop playback"""
        if self.player:
            self.player.stop()

    def pause(self) -> None:
        """Pause playback"""
        if self.player:
            self.player.pause()

    def resume(self) -> None:
        """Resume playback"""
        if self.player:
            self.player.resume()

    def is_playing(self) -> bool:
        """Check if music is currently playing"""
        if self.player is None:
            return False

        # Different method names for different players
        if self.player_type == "mpv":
            return self.player.is_playing()
        elif self.player_type == "ffmpeg":
            return self.player.is_playing_now()

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
        if self.player:
            if self.player_type == "ffmpeg":
                self.player.cleanup()
            elif self.player_type == "mpv":
                self.player.stop()

            self.player = None
