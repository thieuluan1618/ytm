#!/usr/bin/env python3
"""
Test script to verify FFmpeg fallback in CLI mode.
Run with: python3 test_ffmpeg_fallback.py -v
"""

import sys
from unittest.mock import patch, MagicMock

# Enable verbose logging
from ytm_cli.verbose_logger import set_verbose

set_verbose(True, "ffmpeg_test.log")

print("\n" + "=" * 70)
print("Testing FFmpeg Fallback in CLI Mode")
print("=" * 70 + "\n")

# Test 1: Init with mpv available
print("\n[Test 1] Initialize with mpv available")
print("-" * 70)
with patch("shutil.which", return_value="/usr/bin/mpv"):
    with patch("builtins.print"):
        from ytm_cli.hybrid_player import CLIHybridPlayerService

        player = CLIHybridPlayerService()
        print(f"✓ Player type: {player.player_type}")
        assert player.player_type == "mpv"
        print("✓ Test passed: mpv preferred over FFmpeg")

# Test 2: Fallback to FFmpeg when mpv unavailable
print("\n[Test 2] Fallback to FFmpeg when mpv unavailable")
print("-" * 70)
with patch("shutil.which", return_value=None):
    # Mock FFmpeg availability
    with patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=True):
        with patch("builtins.print"):
            # Fresh import to get fallback behavior
            import importlib

            importlib.reload(sys.modules["ytm_cli.hybrid_player"])
            from ytm_cli.hybrid_player import CLIHybridPlayerService

            player = CLIHybridPlayerService()
            print(f"✓ Player type: {player.player_type}")
            assert player.player_type == "ffmpeg"
            print("✓ Test passed: Fallback to FFmpeg successful")

# Test 3: No player available
print("\n[Test 3] No player available (mpv and FFmpeg both missing)")
print("-" * 70)
with patch("shutil.which", return_value=None):
    with patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService._check_ffmpeg_available", return_value=False):
        with patch("builtins.print"):
            import importlib

            importlib.reload(sys.modules["ytm_cli.hybrid_player"])
            from ytm_cli.hybrid_player import CLIHybridPlayerService

            player = CLIHybridPlayerService()
            print(f"✓ Player type: {player.player_type}")
            assert player.player_type == "none"
            assert not player.is_available()
            print("✓ Test passed: Graceful failure when no player available")

# Test 4: FFmpeg player method delegation
print("\n[Test 4] FFmpeg player method delegation")
print("-" * 70)
with patch("shutil.which", return_value=None):
    mock_ffmpeg_player = MagicMock()
    mock_ffmpeg_player.play = MagicMock(return_value=True)
    mock_ffmpeg_player.is_playing_now = MagicMock(return_value=True)
    mock_ffmpeg_player.pause = MagicMock()
    mock_ffmpeg_player.resume = MagicMock()
    mock_ffmpeg_player.stop = MagicMock()

    with patch("ytm_cli.tui.ffmpeg_player.FFmpegPlayerService", return_value=mock_ffmpeg_player):
        with patch("builtins.print"):
            import importlib

            importlib.reload(sys.modules["ytm_cli.hybrid_player"])
            from ytm_cli.hybrid_player import CLIHybridPlayerService

            player = CLIHybridPlayerService()

            # Test play
            result = player.play("test_vid", "Test Song")
            assert result is True
            mock_ffmpeg_player.play.assert_called_once_with("test_vid", "Test Song")
            print("✓ play() delegated correctly")

            # Test is_playing
            result = player.is_playing()
            assert result is True
            mock_ffmpeg_player.is_playing_now.assert_called_once()
            print("✓ is_playing() delegated correctly")

            # Test pause
            player.pause()
            mock_ffmpeg_player.pause.assert_called_once()
            print("✓ pause() delegated correctly")

            # Test resume
            player.resume()
            mock_ffmpeg_player.resume.assert_called_once()
            print("✓ resume() delegated correctly")

            # Test stop
            player.stop()
            mock_ffmpeg_player.stop.assert_called_once()
            print("✓ stop() delegated correctly")

print("\n" + "=" * 70)
print("All FFmpeg fallback tests passed! ✓")
print("=" * 70)
print("\nVerbose log saved to: ffmpeg_test.log\n")
