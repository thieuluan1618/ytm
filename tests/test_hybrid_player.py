"""Tests for CLI hybrid player with mpv/pygame fallback"""

import unittest
from unittest.mock import MagicMock, patch, call
import tempfile
import os
from ytm_cli.hybrid_player import CLIHybridPlayerService
from ytm_cli.tui.pygame_player import PygamePlayerService


class TestCLIHybridPlayerInitialization(unittest.TestCase):
    """Test CLIHybridPlayerService initialization"""

    @patch("shutil.which")
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_init_prefers_mpv_when_available(self, mock_pygame_init, mock_which):
        """Should use mpv if it's available in PATH"""
        mock_which.return_value = "/usr/bin/mpv"

        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "mpv"
        assert player.pygame_player is None
        mock_pygame_init.assert_not_called()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_init_falls_back_to_pygame_when_mpv_unavailable(
        self, mock_pygame_init, mock_which
    ):
        """Should fall back to pygame if mpv is not available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "pygame"
        assert player.pygame_player is not None
        mock_pygame_init.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", side_effect=ImportError("No pygame"))
    def test_init_no_player_available(self, mock_pygame_init, mock_which):
        """Should mark as unavailable if both mpv and pygame fail"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.player_type == "none"
        assert player.pygame_player is None


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
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_is_available_pygame(self, mock_pygame_init, mock_which):
        """Test is_available with pygame fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.is_available() is True
        assert player.player_type == "pygame"

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", side_effect=ImportError("No pygame"))
    def test_is_available_no_player(self, mock_pygame_init, mock_which):
        """Test is_available when no player available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.is_available() is False

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_play_with_pygame_fallback(self, mock_pygame_init, mock_which):
        """Test play method with pygame fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Mock pygame player's play method
        player.pygame_player.play = MagicMock(return_value=True)

        result = player.play("dQw4w9WgXcQ", "Test Song")

        assert result is True
        player.pygame_player.play.assert_called_once_with("dQw4w9WgXcQ", "Test Song")

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_play_failed_with_pygame_fallback(self, mock_pygame_init, mock_which):
        """Test play method failure with pygame fallback"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Mock pygame player's play method to fail
        player.pygame_player.play = MagicMock(return_value=False)

        result = player.play("invalid_id", "Test Song")

        assert result is False

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", side_effect=ImportError("No pygame"))
    def test_play_no_player_available(self, mock_pygame_init, mock_which):
        """Test play method when no player available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        result = player.play("dQw4w9WgXcQ", "Test Song")

        assert result is False

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_stop_pygame(self, mock_pygame_init, mock_which):
        """Test stop method with pygame"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.pygame_player.stop = MagicMock()

        player.stop()

        player.pygame_player.stop.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_pause_pygame(self, mock_pygame_init, mock_which):
        """Test pause method with pygame"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.pygame_player.pause = MagicMock()

        player.pause()

        player.pygame_player.pause.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_resume_pygame(self, mock_pygame_init, mock_which):
        """Test resume method with pygame"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.pygame_player.resume = MagicMock()

        player.resume()

        player.pygame_player.resume.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_is_playing_pygame(self, mock_pygame_init, mock_which):
        """Test is_playing method with pygame"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.pygame_player.is_playing_now = MagicMock(return_value=True)

        result = player.is_playing()

        assert result is True
        player.pygame_player.is_playing_now.assert_called_once()

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_cleanup_pygame(self, mock_pygame_init, mock_which):
        """Test cleanup method with pygame"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        # Create a proper mock player
        mock_player = MagicMock()
        player.pygame_player = mock_player
        player.player_type = "pygame"

        player.cleanup()

        # cleanup() calls stop() first, then pygame_player.cleanup()
        mock_player.stop.assert_called_once()
        mock_player.cleanup.assert_called_once()
        assert player.pygame_player is None


class TestCLIHybridPlayerInfo(unittest.TestCase):
    """Test CLIHybridPlayerService info methods"""

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", return_value=None)
    def test_get_player_info_pygame_available(self, mock_pygame_init, mock_which):
        """Test get_player_info with pygame available"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.pygame_player.is_playing_now = MagicMock(return_value=False)

        info = player.get_player_info()

        assert info["type"] == "pygame"
        assert info["available"] is True
        assert info["playing"] is False

    @patch("shutil.which", return_value=None)
    @patch.object(PygamePlayerService, "__init__", side_effect=ImportError("No pygame"))
    def test_get_player_info_no_player(self, mock_pygame_init, mock_which):
        """Test get_player_info with no player"""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        info = player.get_player_info()

        assert info["type"] == "none"
        assert info["available"] is False
        assert info["playing"] is False


class TestPygamePlayerIntegration(unittest.TestCase):
    """Integration tests for PygamePlayerService"""

    @patch("pygame.mixer.init")
    @patch("yt_dlp.YoutubeDL")
    def test_pygame_player_initialization(self, mock_ytdlp, mock_mixer_init):
        """Test PygamePlayerService initialization"""
        try:
            player = PygamePlayerService()
            assert player.is_initialized is True
        except ImportError:
            self.skipTest("pygame not installed")

    @patch("pygame.mixer.init", side_effect=RuntimeError("Audio device not found"))
    def test_pygame_player_init_failure(self, mock_mixer_init):
        """Test PygamePlayerService init failure"""
        try:
            with self.assertRaises(RuntimeError):
                PygamePlayerService()
        except ImportError:
            self.skipTest("pygame not installed")

    @patch("pygame.mixer.init")
    @patch("pygame.mixer.music.stop")
    def test_pygame_player_stop(self, mock_music_stop, mock_mixer_init):
        """Test PygamePlayerService stop"""
        try:
            player = PygamePlayerService()
            player.stop()
            mock_music_stop.assert_called_once()
        except ImportError:
            self.skipTest("pygame not installed")


if __name__ == "__main__":
    unittest.main()
