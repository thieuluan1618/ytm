"""Tests for CLI hybrid player with mpv/FFmpeg fallback"""

import unittest
from unittest.mock import MagicMock, patch, call
import tempfile
import os
from ytm_cli.hybrid_player import CLIHybridPlayerService
from ytm_cli.tui.ffmpeg_player import FFmpegPlayerService


class TestCLIHybridPlayerInitialization(unittest.TestCase):
    """Test CLIHybridPlayerService initialization"""

    @patch("shutil.which")
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_init_prefers_mpv_when_available(self, mock_ffmpeg_init, mock_which):
        """Should use mpv if it's available in PATH"""
        mock_which.return_value = "/usr/bin/mpv"

        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "mpv"
        assert player.ffmpeg_player is None
        mock_ffmpeg_init.assert_not_called()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_init_falls_back_to_ffmpeg_when_mpv_unavailable(
        self, mock_ffmpeg_init, mock_which
    ):
        """Should fall back to FFmpeg if mpv is not available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "ffmpeg"
        assert player.ffmpeg_player is not None
        mock_ffmpeg_init.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", side_effect=ImportError("No FFmpeg"))
    def test_init_no_player_available(self, mock_ffmpeg_init, mock_which):
        """Should mark as unavailable if both mpv and FFmpeg fail"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "none"
        assert player.ffmpeg_player is None


class TestCLIHybridPlayerPlayback(unittest.TestCase):
    """Test CLIHybridPlayerService playback methods"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_socket = tempfile.mktemp(suffix=".sock")

    def tearDown(self):
        """Clean up temp files"""
        if os.path.exists(self.temp_socket):
            os.unlink(self.temp_socket)

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_is_available_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test is_available with FFmpeg fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.is_available() is True
        assert player.player_type == "ffmpeg"

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", side_effect=ImportError("No FFmpeg"))
    def test_is_available_no_player(self, mock_ffmpeg_init, mock_which):
        """Test is_available when no player available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.is_available() is False

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_play_with_ffmpeg_fallback(self, mock_ffmpeg_init, mock_which):
        """Test play method with FFmpeg fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Mock FFmpeg player's play method
        player.ffmpeg_player.play = MagicMock(return_value=True)

        result = player.play("dQw4w9WgXcQ", "Test Song")

        assert result is True
        player.ffmpeg_player.play.assert_called_once_with("dQw4w9WgXcQ", "Test Song")

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_play_failed_with_ffmpeg_fallback(self, mock_ffmpeg_init, mock_which):
        """Test play method failure with FFmpeg fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Mock FFmpeg player's play method to fail
        player.ffmpeg_player.play = MagicMock(return_value=False)

        result = player.play("invalid_id", "Test Song")

        assert result is False

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", side_effect=ImportError("No FFmpeg"))
    def test_play_no_player_available(self, mock_ffmpeg_init, mock_which):
        """Test play method when no player available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        result = player.play("dQw4w9WgXcQ", "Test Song")

        assert result is False

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_stop_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test stop method with FFmpeg"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.ffmpeg_player.stop = MagicMock()

        player.stop()

        player.ffmpeg_player.stop.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_pause_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test pause method with FFmpeg"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.ffmpeg_player.pause = MagicMock()

        player.pause()

        player.ffmpeg_player.pause.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_resume_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test resume method with FFmpeg"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.ffmpeg_player.resume = MagicMock()

        player.resume()

        player.ffmpeg_player.resume.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_is_playing_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test is_playing method with FFmpeg"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.ffmpeg_player.is_playing_now = MagicMock(return_value=True)

        result = player.is_playing()

        assert result is True
        player.ffmpeg_player.is_playing_now.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_cleanup_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """Test cleanup method with FFmpeg"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Create a proper mock player
        mock_player = MagicMock()
        player.ffmpeg_player = mock_player
        player.player_type = "ffmpeg"

        player.cleanup()

        # cleanup() calls stop() first, then ffmpeg_player.cleanup()
        mock_player.stop.assert_called_once()
        mock_player.cleanup.assert_called_once()
        assert player.ffmpeg_player is None


class TestCLIHybridPlayerInfo(unittest.TestCase):
    """Test CLIHybridPlayerService info methods"""

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_get_player_info_ffmpeg_available(self, mock_ffmpeg_init, mock_which):
        """Test get_player_info with FFmpeg available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.ffmpeg_player.is_playing_now = MagicMock(return_value=False)

        info = player.get_player_info()

        assert info["type"] == "ffmpeg"
        assert info["available"] is True
        assert info["playing"] is False

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", side_effect=ImportError("No FFmpeg"))
    def test_get_player_info_no_player(self, mock_ffmpeg_init, mock_which):
        """Test get_player_info with no player"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        info = player.get_player_info()

        assert info["type"] == "none"
        assert info["available"] is False
        assert info["playing"] is False


class TestFFmpegPlayerIntegration(unittest.TestCase):
    """Integration tests for FFmpegPlayerService"""

    @patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=True)
    @patch("yt_dlp.YoutubeDL")
    def test_ffmpeg_player_initialization(self, mock_ytdlp, mock_ffmpeg_available):
        """Test FFmpegPlayerService initialization"""
        try:
            player = FFmpegPlayerService()
            assert player.is_initialized is True
        except ImportError:
            self.skipTest("FFmpeg not installed")

    @patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=False)
    def test_ffmpeg_player_init_failure(self, mock_ffmpeg_available):
        """Test FFmpegPlayerService init failure"""
        try:
            with self.assertRaises(ImportError):
                FFmpegPlayerService()
        except ImportError:
            self.skipTest("FFmpeg not installed")

    @patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=True)
    def test_ffmpeg_player_stop(self, mock_ffmpeg_available):
        """Test FFmpegPlayerService stop"""
        try:
            player = FFmpegPlayerService()
            player.is_playing = True
            player.ffplay_process = MagicMock()
            player.ffplay_process.terminate = MagicMock()
            player.ffplay_process.wait = MagicMock()
            player.stop()
            player.ffplay_process.terminate.assert_called_once()
            player.ffplay_process.wait.assert_called_once()
        except ImportError:
            self.skipTest("FFmpeg not installed")


if __name__ == "__main__":
    unittest.main()
