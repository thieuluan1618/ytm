"""FFmpeg-based player service as fallback when mpv is not available"""

import signal
import subprocess
import threading
import time
from typing import Optional

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

from ytm_cli.verbose_logger import log_error, log_info, log_section, log_warning


class FFmpegPlayerService:
    """FFmpeg-based background player for streaming music using ffplay"""

    def __init__(self):
        # Check for FFmpeg availability
        if not self._check_ffmpeg_available():
            raise ImportError(
                "FFmpeg is not installed or ffplay is not available. "
                "Install FFmpeg with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
            )

        if not YTDLP_AVAILABLE:
            log_warning("yt-dlp not available - FFmpeg player will not work properly")
            print("⚠️ yt-dlp not available - FFmpeg player will not work properly")
            print("   Install with: pip install yt-dlp")

        self.is_initialized = True
        self.is_playing = False
        self.is_paused = False
        self.current_video_id: Optional[str] = None
        self.ffplay_process: Optional[subprocess.Popen] = None
        self.playback_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        log_info("FFmpeg player initialized successfully")
        print("✓ FFmpeg player ready for playback")

    def _check_ffmpeg_available(self) -> bool:
        """Check if ffplay is available"""
        try:
            result = subprocess.run(
                ["ffplay", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False

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

            # Stop any existing playback and wait for it to finish
            self.stop()

            # Reset stop event for new playback
            self._stop_event.clear()

            with self._lock:
                self.current_video_id = video_id
                self.is_playing = True # Mark as playing immediately to prevent race in UI checks

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
            log_error(f"Error starting FFmpeg playback: {e}")
            print(f"Error starting FFmpeg playback: {e}")
            with self._lock:
                self.is_playing = False
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
            log_section("FFmpeg Playback", "🎵")
            log_info(f"Title: {title}")
            print(f"🎵 {title}")

            # Check stop event before expensive operation
            if self._stop_event.is_set():
                log_info("Playback stopped before URL extraction")
                return

            # Extract stream URL using yt-dlp
            stream_url = self._get_stream_url(youtube_url)
            if not stream_url:
                log_error("Failed to get audio stream URL")
                print("❌ Failed to get audio stream URL")
                with self._lock:
                    self.is_playing = False
                return

            # Check stop event again after extraction
            if self._stop_event.is_set():
                log_info("Playback stopped after URL extraction")
                with self._lock:
                    self.is_playing = False
                return

            log_info("Stream URL extracted successfully")
            print("🔗 Extracted stream URL for FFmpeg playback")

            with self._lock:
                # Final check before starting process
                if self._stop_event.is_set():
                    self.is_playing = False
                    return

                self.is_paused = False

                # Build ffplay command
                # -nodisp: no video display
                # -autoexit: exit when playback finishes
                # -loglevel quiet: suppress ffplay output
                ffplay_cmd = [
                    "ffplay",
                    "-nodisp",           # No video display
                    "-autoexit",         # Exit when playback finishes
                    "-loglevel", "quiet", # Suppress ffplay output
                    stream_url
                ]

                try:
                    # Start ffplay process
                    self.ffplay_process = subprocess.Popen(
                        ffplay_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    log_info("ffplay process started successfully")
                except Exception as proc_error:
                    log_error(f"Failed to start ffplay process: {proc_error}")
                    print(f"❌ Failed to start ffplay: {proc_error}")
                    self.is_playing = False
                    return

            # Wait for process to finish (song ends or is stopped)
            # We check both process status and internal flags
            while not self._stop_event.is_set():
                with self._lock:
                    if not self.ffplay_process:
                        break
                    if self.ffplay_process.poll() is not None:
                        # Process finished naturally
                        log_info("Stream ended naturally")
                        print("✅ Song finished")
                        break
                time.sleep(0.1)

            with self._lock:
                self.is_playing = False
                self.ffplay_process = None

            log_info("Playback finished successfully")

        except Exception as e:
            log_error(f"FFmpeg playback error: {e}")
            print(f"❌ FFmpeg playback error: {e}")
            with self._lock:
                self.is_playing = False
        finally:
             pass # Cleanup handled in specific blocks or stop()

    def stop(self) -> None:
        """Stop current playback"""
        try:
            if self.is_initialized:
                # Signal stop to all threads
                self._stop_event.set()

                # Use lock to safely manage process termination
                with self._lock:
                    self.is_playing = False
                    self.is_paused = False
                    self.current_video_id = None

                    # Terminate ffplay process if running
                    if self.ffplay_process:
                        try:
                            self.ffplay_process.terminate()
                            # We can't wait here too long inside lock or we block UI
                            # but subprocess.wait is usually fast if terminate works
                            try:
                                self.ffplay_process.wait(timeout=0.2)
                            except subprocess.TimeoutExpired:
                                self.ffplay_process.kill()
                        except Exception as e:
                            log_error(f"Error terminating process: {e}")
                        finally:
                            self.ffplay_process = None

                # Wait for playback thread to finish outside of lock
                # This is critical to prevent race conditions
                if self.playback_thread and self.playback_thread.is_alive():
                    # Don't wait forever, just enough to let it see the stop event
                    self.playback_thread.join(timeout=2.0)

                self.playback_thread = None

                log_info("Playback stopped")

        except Exception as e:
            log_error(f"Error stopping FFmpeg playback: {e}")
            print(f"Error stopping FFmpeg playback: {e}")

    def pause(self) -> None:
        """Pause playback"""
        try:
            with self._lock:
                if self.is_initialized and self.is_playing and not self.is_paused and self.ffplay_process:
                    # Send SIGSTOP to pause ffplay process
                    self.ffplay_process.send_signal(signal.SIGSTOP)
                    self.is_paused = True
                    log_info("Playback paused")
        except Exception as e:
            log_error(f"Error pausing FFmpeg playback: {e}")

    def resume(self) -> None:
        """Resume playback"""
        try:
            with self._lock:
                if self.is_initialized and self.is_playing and self.is_paused and self.ffplay_process:
                    # Send SIGCONT to resume ffplay process
                    self.ffplay_process.send_signal(signal.SIGCONT)
                    self.is_paused = False
                    log_info("Playback resumed")
        except Exception as e:
            log_error(f"Error resuming FFmpeg playback: {e}")

    def is_playing_now(self) -> bool:
        """Check if playback session is active (loading, playing, or paused)"""
        if not self.is_initialized:
            return False
        try:
            with self._lock:
                # Return simple state flag
                # This covers loading state (process is None but is_playing is True)
                # and paused state (is_paused is True but is_playing is True)
                
                # If we have a process, we can double check it's still alive
                # to catch cases where it crashed/exited but thread hasn't updated yet
                if self.ffplay_process and self.ffplay_process.poll() is not None:
                     self.is_playing = False
                     return False
                     
                return self.is_playing
        except Exception:
            return False

    def get_volume(self) -> float:
        """Get current volume (0.0 to 1.0)"""
        # FFmpeg doesn't provide easy volume control through ffplay
        # Return default volume
        return 1.0

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)"""
        # FFmpeg doesn't provide easy volume control through ffplay
        # This would require restarting the process with audio filters
        log_info(f"Volume control not implemented for FFmpeg player (requested: {volume:.1%})")

    def cleanup(self) -> None:
        """Clean up FFmpeg resources"""
        try:
            self.stop()
            if self.is_initialized:
                self.is_initialized = False
                log_info("FFmpeg player cleaned up")
        except Exception as e:
            log_error(f"Error during FFmpeg cleanup: {e}")
