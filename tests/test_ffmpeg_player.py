"""Tests for FFmpegPlayerService"""

import unittest
import threading
import subprocess
import time
from unittest.mock import MagicMock, patch, Mock, call
from unittest.mock import PropertyMock

import pytest

from ytm_cli.tui.ffmpeg_player import FFmpegPlayerService


class TestFFmpegPlayerServiceInitialization(unittest.TestCase):
    """Test FFmpegPlayerService initialization"""

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("builtins.print")
    def test_init_success(self, mock_print, mock_log, mock_ffmpeg_check):
        """Should initialize successfully when FFmpeg is available"""
        player = FFmpegPlayerService()

        assert player.is_initialized is True
        assert player.is_playing is False
        assert player.is_paused is False
        assert player.current_video_id is None
        assert player.ffplay_process is None
        assert player.playback_thread is None
        mock_ffmpeg_check.assert_called_once()
        mock_log.assert_called_once()
        mock_print.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=False)
    def test_init_failure_no_ffmpeg(self, mock_ffmpeg_check):
        """Should raise ImportError when FFmpeg is not available"""
        with self.assertRaises(ImportError) as cm:
            FFmpegPlayerService()

        assert "FFmpeg is not installed" in str(cm.exception)
        mock_ffmpeg_check.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", False)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_warning")
    @patch("builtins.print")
    def test_init_warning_no_ytdlp(self, mock_print, mock_log_warning, mock_ffmpeg_check):
        """Should warn when yt-dlp is not available but still initialize"""
        player = FFmpegPlayerService()

        assert player.is_initialized is True
        mock_log_warning.assert_called_once_with("yt-dlp not available - FFmpeg player will not work properly")
        mock_print.assert_any_call("⚠️ yt-dlp not available - FFmpeg player will not work properly")
        mock_print.assert_any_call("   Install with: pip install yt-dlp")

    def test_check_ffmpeg_available_success(self):
        """Should return True when ffplay command works"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0

            result = FFmpegPlayerService._check_ffmpeg_available(None)

            assert result is True
            mock_run.assert_called_once_with(
                ["ffplay", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )

    def test_check_ffmpeg_available_failure(self):
        """Should return False when ffplay command fails"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            # Also test timeout/file not found cases
            mock_run.side_effect = [subprocess.TimeoutExpired("ffplay", 5), FileNotFoundError()]

            # Test timeout error
            result = FFmpegPlayerService._check_ffmpeg_available(None)
            assert result is False

            # Test file not found error
            result = FFmpegPlayerService._check_ffmpeg_available(None)
            assert result is False


class TestFFmpegPlayerServicePlayback(unittest.TestCase):
    """Test FFmpegPlayerService playback methods"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_player = Mock(spec=FFmpegPlayerService)
        self.mock_player.is_initialized = True
        self.mock_player.is_playing = False
        self.mock_player.is_paused = False
        self.mock_player.current_video_id = None
        self.mock_player.ffplay_process = None
        self.mock_player.playback_thread = None
        self.mock_player._lock = threading.RLock()
        self.mock_player._stop_event = Mock()

        # Bind real methods for testing
        self.mock_player.play = FFmpegPlayerService.play.__get__(self.mock_player)
        self.mock_player.stop = FFmpegPlayerService.stop.__get__(self.mock_player)
        self.mock_player.is_playing_now = FFmpegPlayerService.is_playing_now.__get__(self.mock_player)

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("builtins.print")
    def test_play_success(self, mock_print, mock_log, mock_ffmpeg_check):
        """Should start playback successfully"""
        player = FFmpegPlayerService()

        with patch.object(player, "_play_stream") as mock_play_stream:
            mock_play_stream.return_value = None
            with patch("threading.Thread") as mock_thread:
                mock_thread_instance = Mock()
                mock_thread.return_value = mock_thread_instance

                result = player.play("test_video_id", "Test Song")

                assert result is True
                assert player.current_video_id == "test_video_id"
                assert player.is_playing is True
                mock_thread.assert_called_once()
                mock_thread_instance.start.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("builtins.print")
    def test_play_not_initialized(self, mock_print, mock_log, mock_ffmpeg_check):
        """Should return False when player is not initialized"""
        player = FFmpegPlayerService()
        player.is_initialized = False

        result = player.play("test_video_id", "Test Song")

        assert result is False

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_error")
    @patch("builtins.print")
    def test_play_setup_exception(self, mock_print, mock_log_error, mock_log, mock_ffmpeg_check):
        """Should handle exceptions during play setup (not thread execution)"""
        player = FFmpegPlayerService()

        # Mock the stop method to raise an exception (this happens during setup)
        with patch.object(player, "stop", side_effect=Exception("Stop error")):
            result = player.play("test_video_id", "Test Song")

            assert result is False
            assert player.is_playing is False
            mock_log_error.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    def test_get_stream_url_success(self):
        """Should extract stream URL successfully"""
        with patch("yt_dlp.YoutubeDL") as mock_ytdlp:
            mock_ydl_instance = Mock()
            mock_ytdlp.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.return_value = {
                "url": "http://example.com/stream.mp3",
                "http_headers": {"User-Agent": "TestAgent"}
            }

            player = FFmpegPlayerService._check_ffmpeg_available(None)
            if isinstance(player, bool):  # Mock the check
                player = Mock()
                player.YTDLP_AVAILABLE = True

            stream_url, headers = FFmpegPlayerService._get_stream_url(player, "http://youtube.com/watch?v=test")

            assert stream_url == "http://example.com/stream.mp3"
            assert headers == {"User-Agent": "TestAgent"}

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", False)
    def test_get_stream_url_no_ytdlp(self):
        """Should return None when yt-dlp is not available"""
        with patch("builtins.print"):
            stream_url, headers = FFmpegPlayerService._get_stream_url(None, "http://youtube.com/watch?v=test")

        assert stream_url is None
        assert headers is None

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    def test_get_stream_url_extraction_failure(self):
        """Should handle extraction failures gracefully"""
        with patch("yt_dlp.YoutubeDL") as mock_ytdlp:
            mock_ydl_instance = Mock()
            mock_ytdlp.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.return_value = {"no_url": "here"}

            with patch("builtins.print"):
                stream_url, headers = FFmpegPlayerService._get_stream_url(None, "http://youtube.com/watch?v=test")

            assert stream_url is None
            assert headers is None

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    def test_get_stream_url_exception(self):
        """Should handle exceptions during stream URL extraction"""
        with patch("yt_dlp.YoutubeDL", side_effect=Exception("yt-dlp error")):
            with patch("ytm_cli.tui.ffmpeg_player.log_error"), patch("builtins.print"):
                stream_url, headers = FFmpegPlayerService._get_stream_url(None, "http://youtube.com/watch?v=test")

            assert stream_url is None
            assert headers is None


class TestFFmpegPlayerServiceControls(unittest.TestCase):
    """Test FFmpegPlayerService control methods"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True), \
             patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True), \
             patch("ytm_cli.tui.ffmpeg_player.log_info"), \
             patch("builtins.print"):
            self.player = FFmpegPlayerService()

    def test_pause_success(self):
        """Should pause playback successfully"""
        mock_process = Mock()
        self.player.ffplay_process = mock_process
        self.player.is_playing = True
        self.player.is_paused = False

        with patch("signal.SIGSTOP", 123):
            self.player.pause()

            mock_process.send_signal.assert_called_once_with(123)
            assert self.player.is_paused is True

    def test_pause_not_playing(self):
        """Should not pause when not playing"""
        self.player.is_playing = False

        self.player.pause()

        # Should not attempt to send signal
        assert self.player.is_paused is False

    def test_pause_no_process(self):
        """Should not pause when no process exists"""
        self.player.is_playing = True
        self.player.is_paused = False
        self.player.ffplay_process = None

        self.player.pause()

        assert self.player.is_paused is False

    def test_resume_success(self):
        """Should resume playback successfully"""
        mock_process = Mock()
        self.player.ffplay_process = mock_process
        self.player.is_playing = True
        self.player.is_paused = True

        with patch("signal.SIGCONT", 456):
            self.player.resume()

            mock_process.send_signal.assert_called_once_with(456)
            assert self.player.is_paused is False

    def test_resume_not_paused(self):
        """Should not resume when not paused"""
        self.player.is_playing = True
        self.player.is_paused = False

        self.player.resume()

        # Should not attempt to send signal
        assert self.player.is_paused is False

    @patch("ytm_cli.tui.ffmpeg_player.log_error")
    def test_pause_exception(self, mock_log_error):
        """Should handle exceptions during pause"""
        mock_process = Mock()
        mock_process.send_signal.side_effect = Exception("Signal error")
        self.player.ffplay_process = mock_process
        self.player.is_playing = True
        self.player.is_paused = False

        self.player.pause()

        mock_log_error.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.log_error")
    def test_resume_exception(self, mock_log_error):
        """Should handle exceptions during resume"""
        mock_process = Mock()
        mock_process.send_signal.side_effect = Exception("Signal error")
        self.player.ffplay_process = mock_process
        self.player.is_playing = True
        self.player.is_paused = True

        self.player.resume()

        mock_log_error.assert_called_once()


class TestFFmpegPlayerServiceState(unittest.TestCase):
    """Test FFmpegPlayerService state management"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True), \
             patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True), \
             patch("ytm_cli.tui.ffmpeg_player.log_info"), \
             patch("builtins.print"):
            self.player = FFmpegPlayerService()

    def test_is_playing_now_true(self):
        """Should return True when playing"""
        self.player.is_initialized = True
        self.player.is_playing = True
        self.player.ffplay_process = None  # Loading state

        result = self.player.is_playing_now()

        assert result is True

    def test_is_playing_now_false_not_initialized(self):
        """Should return False when not initialized"""
        self.player.is_initialized = False

        result = self.player.is_playing_now()

        assert result is False

    def test_is_playing_now_process_finished(self):
        """Should return False when process has finished"""
        self.player.is_initialized = True
        self.player.is_playing = True
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process finished
        self.player.ffplay_process = mock_process

        result = self.player.is_playing_now()

        assert result is False
        assert self.player.is_playing is False

    def test_is_playing_now_exception(self):
        """Should return False on exception"""
        self.player.is_initialized = True
        self.player.is_playing = True
        self.player.ffplay_process = Mock()
        self.player.ffplay_process.poll.side_effect = Exception("Poll error")

        result = self.player.is_playing_now()

        assert result is False


class TestFFmpegPlayerServiceVolume(unittest.TestCase):
    """Test FFmpegPlayerService volume control"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True), \
             patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True), \
             patch("ytm_cli.tui.ffmpeg_player.log_info"), \
             patch("builtins.print"):
            self.player = FFmpegPlayerService()

    def test_get_volume(self):
        """Should return default volume"""
        result = self.player.get_volume()
        assert result == 1.0

    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    def test_set_volume(self, mock_log):
        """Should log volume set attempt (not implemented)"""
        self.player.set_volume(0.5)

        mock_log.assert_called_once_with("Volume control not implemented for FFmpeg player (requested: 50.0%)")


class TestFFmpegPlayerServiceCleanup(unittest.TestCase):
    """Test FFmpegPlayerService cleanup"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True), \
             patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True), \
             patch("ytm_cli.tui.ffmpeg_player.log_info"), \
             patch("builtins.print"):
            self.player = FFmpegPlayerService()

    def test_cleanup(self):
        """Should clean up resources properly"""
        # Set up some state
        self.player.is_playing = True
        self.player.current_video_id = "test_id"

        with patch.object(self.player, "stop") as mock_stop:
            self.player.cleanup()

            mock_stop.assert_called_once()
            assert self.player.is_initialized is False

    @patch("ytm_cli.tui.ffmpeg_player.log_error")
    def test_cleanup_exception(self, mock_log_error):
        """Should handle exceptions during cleanup"""
        with patch.object(self.player, "stop", side_effect=Exception("Stop error")):
            self.player.cleanup()

            mock_log_error.assert_called_once()


class TestFFmpegPlayerServiceStop(unittest.TestCase):
    """Test FFmpegPlayerService stop functionality"""

    def setUp(self):
        """Set up test fixtures"""
        with patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True), \
             patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True), \
             patch("ytm_cli.tui.ffmpeg_player.log_info"), \
             patch("builtins.print"):
            self.player = FFmpegPlayerService()

    def test_stop_no_process(self):
        """Should handle stop when no process is running"""
        self.player.is_playing = True
        self.player.current_video_id = "test_id"

        self.player.stop()

        assert self.player.is_playing is False
        assert self.player.current_video_id is None

    def test_stop_with_process(self):
        """Should stop running process correctly"""
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.terminate.return_value = None
        mock_process.wait.return_value = 0

        mock_thread = Mock()
        mock_thread.is_alive.return_value = True

        self.player.ffplay_process = mock_process
        self.player.playback_thread = mock_thread
        self.player.is_playing = True
        self.player.current_video_id = "test_id"

        self.player.stop()

        assert self.player.is_playing is False
        assert self.player.current_video_id is None
        assert self.player.ffplay_process is None
        mock_process.terminate.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=2.0)

    def test_stop_process_timeout(self):
        """Should kill process if terminate times out"""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("ffplay", 0.2)
        mock_process.kill.return_value = None

        self.player.ffplay_process = mock_process
        self.player.is_playing = True

        self.player.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @patch("ytm_cli.tui.ffmpeg_player.log_error")
    def test_stop_process_exception(self, mock_log_error):
        """Should handle exceptions during process termination"""
        mock_process = Mock()
        mock_process.terminate.side_effect = Exception("Terminate error")

        self.player.ffplay_process = mock_process
        self.player.is_playing = True

        self.player.stop()

        mock_log_error.assert_called_once()


class TestFFmpegPlayerServicePlayStream(unittest.TestCase):
    """Test FFmpegPlayerService _play_stream method"""

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_section")
    @patch("builtins.print")
    def test_play_stream_stopped_early(self, mock_print, mock_log_section, mock_log, mock_ffmpeg_check):
        """Should handle stop event before URL extraction"""
        player = FFmpegPlayerService()
        player._stop_event.set()  # Set stop event

        with patch.object(player, "_get_stream_url") as mock_get_url:
            player._play_stream("http://youtube.com/watch?v=test", "Test Song")

            # Should not attempt URL extraction
            mock_get_url.assert_not_called()

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_section")
    @patch("builtins.print")
    def test_play_stream_no_url(self, mock_print, mock_log_section, mock_log, mock_ffmpeg_check):
        """Should handle failure to get stream URL"""
        player = FFmpegPlayerService()

        with patch.object(player, "_get_stream_url", return_value=(None, None)):
            player._play_stream("http://youtube.com/watch?v=test", "Test Song")

            assert player.is_playing is False

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_section")
    @patch("builtins.print")
    @patch("subprocess.Popen")
    def test_play_stream_process_start_failure(self, mock_popen, mock_print, mock_log_section, mock_log, mock_ffmpeg_check):
        """Should handle ffplay process start failure"""
        player = FFmpegPlayerService()
        mock_popen.side_effect = Exception("Process start error")

        with patch.object(player, "_get_stream_url", return_value=("http://stream.url", {"User-Agent": "test"})):
            player._play_stream("http://youtube.com/watch?v=test", "Test Song")

            assert player.is_playing is False

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_section")
    @patch("builtins.print")
    @patch("subprocess.Popen")
    @patch("time.sleep")
    def test_play_stream_natural_end(self, mock_sleep, mock_popen, mock_print, mock_log_section, mock_log, mock_ffmpeg_check):
        """Should handle stream ending naturally"""
        player = FFmpegPlayerService()

        # Mock process that ends naturally
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Still running, then finished
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = b""
        mock_popen.return_value = mock_process

        with patch.object(player, "_get_stream_url", return_value=("http://stream.url", {"User-Agent": "test"})):
            # Simulate the while loop ending after 3 iterations
            def sleep_side_effect(duration):
                if mock_sleep.call_count >= 3:
                    player._stop_event.set()  # End the loop

            mock_sleep.side_effect = sleep_side_effect

            player._play_stream("http://youtube.com/watch?v=test", "Test Song")

            assert player.is_playing is False

    @patch("ytm_cli.tui.ffmpeg_player.YTDLP_AVAILABLE", True)
    @patch.object(FFmpegPlayerService, "_check_ffmpeg_available", return_value=True)
    @patch("ytm_cli.tui.ffmpeg_player.log_info")
    @patch("ytm_cli.tui.ffmpeg_player.log_section")
    @patch("builtins.print")
    def test_play_stream_exception(self, mock_print, mock_log_section, mock_log, mock_ffmpeg_check):
        """Should handle exceptions in _play_stream"""
        player = FFmpegPlayerService()

        with patch.object(player, "_get_stream_url", side_effect=Exception("Stream error")):
            player._play_stream("http://youtube.com/watch?v=test", "Test Song")

            assert player.is_playing is False


if __name__ == "__main__":
    unittest.main()