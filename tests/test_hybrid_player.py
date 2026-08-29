"""Tests for CLI hybrid player with mpv/FFmpeg fallback"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ytm_cli.ffmpeg_player import FFmpegPlayerService
from ytm_cli.hybrid_player import (
    CLIHybridPlayerService,
    ResolvedAudio,
    _is_ytdlp_outdated,
    resolve_audio_url,
)


def test_ytdlp_version_check_handles_date_versions():
    """Only releases older than the known-safe yt-dlp version need a warning."""
    assert _is_ytdlp_outdated("2026.7.4") is True
    assert _is_ytdlp_outdated("2026.8.19") is False
    assert _is_ytdlp_outdated("2026.10.1") is False
    assert _is_ytdlp_outdated("unknown") is False


def test_resolve_audio_url_includes_required_user_agent():
    """Return the request metadata required to play a direct stream URL."""
    result = MagicMock(
        returncode=0,
        stdout=('https://example.test/audio\n{"User-Agent": "Test Browser", "Accept": "*/*"}\n'),
    )

    with (
        patch("ytm_cli.hybrid_player.get_cookies_browser", return_value=None),
        patch("ytm_cli.hybrid_player.subprocess.run", return_value=result),
    ):
        resolved = resolve_audio_url("video-id")

    assert resolved == ResolvedAudio("https://example.test/audio", "Test Browser")


class TestCLIHybridPlayerInitialization(unittest.TestCase):
    """Test CLIHybridPlayerService initialization"""

    @patch("ytm_cli.hybrid_player.YTDLP_VERSION", "2026.7.4")
    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_init_suggests_updating_outdated_ytdlp(self, mock_which):
        """An incompatible yt-dlp release should produce an actionable warning."""
        with patch("builtins.print") as mock_print:
            CLIHybridPlayerService()

        mock_print.assert_any_call(
            "⚠ yt-dlp 2026.7.4 is outdated and may cause songs to skip."
        )
        mock_print.assert_any_call("  Run ytm-cli --update to install 2026.8.19 or newer.")

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
    def test_init_falls_back_to_ffmpeg_when_mpv_unavailable(self, mock_ffmpeg_init, mock_which):
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

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_is_playing_ignores_mpv_idle_during_startup(self, mock_which):
        """A transient idle state before MPV loads the file must not skip it."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.mpv_process = MagicMock()
        player.mpv_process.poll.return_value = None
        player.socket_path = self.temp_socket

        with (
            patch("ytm_cli.hybrid_player.os.path.exists", return_value=True),
            patch.object(player, "_get_mpv_property", return_value=True),
        ):
            assert player.is_playing() is True

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_is_playing_detects_mpv_idle_after_playback_started(self, mock_which):
        """An idle state after an active file means the track has ended."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        player.mpv_process = MagicMock()
        player.mpv_process.poll.return_value = None
        player.socket_path = self.temp_socket

        with (
            patch("ytm_cli.hybrid_player.os.path.exists", return_value=True),
            patch.object(player, "_get_mpv_property", side_effect=[False, True]),
        ):
            assert player.is_playing() is True
            assert player.is_playing() is False

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_play_mpv_passes_resolved_user_agent(self, mock_which):
        """mpv must use the user agent associated with a direct stream URL."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        process = MagicMock(pid=123)
        process.poll.return_value = None
        resolved = ResolvedAudio("https://example.test/audio", "Test Browser")

        with (
            patch("ytm_cli.hybrid_player.get_mpv_flags", return_value=["--no-video"]),
            patch("ytm_cli.hybrid_player.save_player_pid"),
            patch("ytm_cli.hybrid_player.subprocess.Popen", return_value=process) as mock_popen,
            patch("ytm_cli.hybrid_player.os.path.exists", return_value=True),
            patch("ytm_cli.hybrid_player.time.sleep"),
        ):
            assert player.play("video-id", "Test Song", resolved) is True

        command = mock_popen.call_args.args[0]
        assert command[1] == resolved.url
        assert "--user-agent=Test Browser" in command

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_play_mpv_passes_user_agent_when_stream_is_unresolved(self, mock_which):
        """mpv's yt-dlp fallback must not request media as libmpv."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        process = MagicMock(pid=123)
        process.poll.return_value = None

        with (
            patch("ytm_cli.hybrid_player.get_mpv_flags", return_value=["--no-video"]),
            patch("ytm_cli.hybrid_player.get_cookies_browser", return_value=None),
            patch("ytm_cli.hybrid_player.save_player_pid"),
            patch("ytm_cli.hybrid_player.subprocess.Popen", return_value=process) as mock_popen,
            patch("ytm_cli.hybrid_player.os.path.exists", return_value=True),
            patch("ytm_cli.hybrid_player.time.sleep"),
        ):
            assert player.play("video-id", "Test Song") is True

        command = mock_popen.call_args.args[0]
        assert any(flag.startswith("--user-agent=Mozilla/") for flag in command)

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_play_mpv_routes_next_media_keys_to_cli(self, mock_which):
        """MPV's OS Next controls should set the property consumed by the CLI queue."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        process = MagicMock(pid=123)
        process.poll.return_value = None
        loaded_bindings = []

        def capture_bindings(command, expect_response=False):
            assert expect_response is True
            config_path = command["command"][1]
            with open(config_path, encoding="utf-8") as config:
                loaded_bindings.append(config.read())
            return True

        with (
            patch("ytm_cli.hybrid_player.get_mpv_flags", return_value=["--no-video"]),
            patch("ytm_cli.hybrid_player.get_cookies_browser", return_value=None),
            patch("ytm_cli.hybrid_player.save_player_pid"),
            patch("ytm_cli.hybrid_player.subprocess.Popen", return_value=process),
            patch("ytm_cli.hybrid_player.os.path.exists", return_value=True),
            patch("ytm_cli.hybrid_player.time.sleep"),
            patch.object(player, "_send_mpv_command", side_effect=capture_bindings),
        ):
            assert player.play("video-id", "Test Song") is True

        assert loaded_bindings == [
            "NEXT no-osd set pause yes; no-osd set time-pos 0; "
            "no-osd set user-data/ytm-cli/next-requested yes\n"
            "XF86_NEXT no-osd set pause yes; no-osd set time-pos 0; "
            "no-osd set user-data/ytm-cli/next-requested yes\n"
        ]

    @patch("shutil.which", return_value="/usr/bin/mpv")
    def test_consume_next_request_resets_mpv_signal(self, mock_which):
        """A media-key signal should be consumed once before the CLI advances."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()
        player.socket_path = self.temp_socket

        with (
            patch.object(player, "_get_mpv_property", return_value="yes"),
            patch.object(player, "_send_mpv_command", return_value=True) as mock_send,
        ):
            assert player.consume_next_request() is True

        mock_send.assert_called_once_with(
            {
                "command": [
                    "set_property",
                    "user-data/ytm-cli/next-requested",
                    False,
                ]
            }
        )

    @patch("shutil.which", return_value=None)
    @patch.object(FFmpegPlayerService, "__init__", return_value=None)
    def test_consume_next_request_ignores_ffmpeg(self, mock_ffmpeg_init, mock_which):
        """The mpv-only media bridge must not affect the FFmpeg fallback."""
        with patch("builtins.print"):
            player = CLIHybridPlayerService()

        assert player.consume_next_request() is False

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

    @patch("ytm_cli.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=True)
    @patch("yt_dlp.YoutubeDL")
    def test_ffmpeg_player_initialization(self, mock_ytdlp, mock_ffmpeg_available):
        """Test FFmpegPlayerService initialization"""
        try:
            player = FFmpegPlayerService()
            assert player.is_initialized is True
        except ImportError:
            self.skipTest("FFmpeg not installed")

    @patch("ytm_cli.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=False)
    def test_ffmpeg_player_init_failure(self, mock_ffmpeg_available):
        """Test FFmpegPlayerService init failure"""
        try:
            with self.assertRaises(ImportError):
                FFmpegPlayerService()
        except ImportError:
            self.skipTest("FFmpeg not installed")

    @patch("ytm_cli.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=True)
    def test_ffmpeg_player_stop(self, mock_ffmpeg_available):
        """Test FFmpegPlayerService stop"""
        try:
            player = FFmpegPlayerService()
            player.is_playing = True
            mock_process = MagicMock()
            mock_process.terminate = MagicMock()
            mock_process.wait = MagicMock()
            mock_process.kill = MagicMock()
            player.ffplay_process = mock_process
            player.stop()
            mock_process.terminate.assert_called_once()
        except ImportError:
            self.skipTest("FFmpeg not installed")


if __name__ == "__main__":
    unittest.main()
