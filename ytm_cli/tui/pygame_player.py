"""Pygame-based player service as fallback when mpv is not available"""

import threading
import time
from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

from ytm_cli.verbose_logger import log_error, log_info, log_section, log_warning


class PygamePlayerService:
    """Pygame-based background player for streaming music"""

    def __init__(self):
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame is not installed. Install with: pip install pygame")

        if not YTDLP_AVAILABLE:
            log_warning("yt-dlp not available - pygame player will not work properly")
            print("⚠️ yt-dlp not available - pygame player will not work properly")
            print("   Install with: pip install yt-dlp")

        self.is_initialized = False
        self.is_playing = False
        self.is_paused = False
        self.current_video_id: Optional[str] = None
        self.playback_thread: Optional[threading.Thread] = None

        try:
            pygame.mixer.init()
            self.is_initialized = True
            log_info("Pygame mixer initialized successfully")
        except Exception as e:
            log_error(f"Failed to initialize pygame mixer: {e}")
            raise RuntimeError(
                f"Failed to initialize pygame mixer: {e}"
            ) from e

    def play(self, video_id: str, title: str = "") -> bool:
        """Start playing a song

        Args:
            video_id: YouTube video ID
            title: Song title for logging

        Returns:
            True if playback started successfully
        """
        try:
            if not self.is_initialized:
                return False

            # Stop any existing playback
            self.stop()

            self.current_video_id = video_id

            # Build YouTube URL for yt-dlp extraction
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"

            # Start playback in background thread to avoid blocking
            self.playback_thread = threading.Thread(
                target=self._play_stream,
                args=(youtube_url, title),
                daemon=True,
            )
            self.playback_thread.start()

            return True

        except Exception as e:
            log_error(f"Error starting pygame playback: {e}")
            print(f"Error starting pygame playback: {e}")
            return False

    def _get_stream_url(self, youtube_url: str) -> Optional[str]:
        """Extract audio stream URL using yt-dlp"""
        try:
            if not YTDLP_AVAILABLE:
                print("❌ yt-dlp not available for stream extraction")
                return None

            ydl_opts = {
                'format': 'bestaudio[abr<=128]/bestaudio',  # Prefer lower bitrate for streaming
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                if info and 'url' in info:
                    return info['url']
                else:
                    print("❌ Could not extract stream URL")
                    return None

        except Exception as e:
            log_error(f"Error extracting stream URL: {e}")
            print(f"❌ Error extracting stream URL: {e}")
            return None

    def _play_stream(self, youtube_url: str, title: str) -> None:
        """Internal method to handle playback in a thread"""
        try:
            log_section("Pygame Playback", "🎵")
            log_info(f"Title: {title}")
            print(f"🎵 {title}")

            # Extract stream URL using yt-dlp
            stream_url = self._get_stream_url(youtube_url)
            if not stream_url:
                log_error("Failed to get audio stream URL")
                print("❌ Failed to get audio stream URL")
                return

            log_info("Stream URL extracted successfully")
            print("🔗 Extracted stream URL for pygame playback")
            self.is_playing = True
            self.is_paused = False

            # Load and play the stream
            try:
                pygame.mixer.music.load(stream_url)
                log_info("Stream loaded into pygame mixer")
                pygame.mixer.music.play()
            except Exception as load_error:
                log_error(f"Failed to load stream into mixer: {load_error}")
                print(f"❌ Failed to load stream: {load_error}")
                print("Note: Pygame mixer may not support this stream format.")
                print("Consider using MPV player instead (install with: brew install mpv)")
                self.is_playing = False
                return

            # Keep playing until the song ends or is stopped
            # For streaming URLs, we wait longer before checking status
            start_time = time.time()
            max_duration = 600  # 10 minutes max per song
            initial_wait = 1.0  # Wait 1 second before checking if music is busy

            while self.is_playing:
                elapsed = time.time() - start_time

                # Don't check playback status immediately (streaming takes time to start)
                if elapsed < initial_wait:
                    time.sleep(0.1)
                    continue

                # Check if music is still playing
                is_busy = pygame.mixer.music.get_busy()

                if not is_busy:
                    log_info("Stream ended or stopped")
                    break

                # Safety timeout
                if elapsed > max_duration:
                    log_warning(f"Playback timeout after {max_duration}s")
                    break

                time.sleep(0.1)

            self.is_playing = False
            log_info("Playback finished successfully")
            print("✅ Song finished")

        except Exception as e:
            log_error(f"Pygame playback error: {e}")
            print(f"❌ Pygame playback error: {e}")
            self.is_playing = False

    def stop(self) -> None:
        """Stop current playback"""
        try:
            if self.is_initialized:
                pygame.mixer.music.stop()
                self.is_playing = False
                self.is_paused = False
                self.current_video_id = None

                # Wait for playback thread to finish
                if self.playback_thread and self.playback_thread.is_alive():
                    self.playback_thread.join(timeout=1)

                log_info("Playback stopped")

        except Exception as e:
            log_error(f"Error stopping pygame playback: {e}")
            print(f"Error stopping pygame playback: {e}")

    def pause(self) -> None:
        """Pause playback"""
        try:
            if self.is_initialized and self.is_playing and not self.is_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
                log_info("Playback paused")
        except Exception as e:
            log_error(f"Error pausing pygame playback: {e}")

    def resume(self) -> None:
        """Resume playback"""
        try:
            if self.is_initialized and self.is_playing and self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False
                log_info("Playback resumed")
        except Exception as e:
            log_error(f"Error resuming pygame playback: {e}")

    def is_playing_now(self) -> bool:
        """Check if music is currently playing"""
        if not self.is_initialized:
            return False
        try:
            return pygame.mixer.music.get_busy() and not self.is_paused
        except Exception:
            return False

    def get_volume(self) -> float:
        """Get current volume (0.0 to 1.0)"""
        try:
            return pygame.mixer.music.get_volume()
        except Exception:
            return 1.0

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        try:
            if 0.0 <= volume <= 1.0:
                pygame.mixer.music.set_volume(volume)
                log_info(f"Volume set to {volume:.1%}")
        except Exception as e:
            log_error(f"Error setting pygame volume: {e}")

    def cleanup(self) -> None:
        """Clean up pygame resources"""
        try:
            self.stop()
            if self.is_initialized:
                pygame.mixer.quit()
                self.is_initialized = False
                log_info("Pygame mixer cleaned up")
        except Exception as e:
            log_error(f"Error during pygame cleanup: {e}")
