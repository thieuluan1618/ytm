#!/usr/bin/env python3
"""
Test script to verify pygame fallback in CLI mode.
Run with: python3 test_pygame_fallback.py -v
"""

import sys
from unittest.mock import patch, MagicMock

# Enable verbose logging
from ytm_cli.verbose_logger import set_verbose

set_verbose(True, "pygame_test.log")

print("\n" + "=" * 70)
print("Testing Pygame Fallback in CLI Mode")
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
        print("✓ Test passed: mpv preferred over pygame")

# Test 2: Fallback to pygame when mpv unavailable
print("\n[Test 2] Fallback to pygame when mpv unavailable")
print("-" * 70)
with patch("shutil.which", return_value=None):
    # Mock pygame
    mock_pygame = MagicMock()
    mock_pygame.mixer = MagicMock()
    mock_pygame.mixer.init = MagicMock()

    sys.modules["pygame"] = mock_pygame

    with patch("builtins.print"):
        # Fresh import to get fallback behavior
        import importlib

        importlib.reload(sys.modules["ytm_cli.hybrid_player"])
        from ytm_cli.hybrid_player import CLIHybridPlayerService

        player = CLIHybridPlayerService()
        print(f"✓ Player type: {player.player_type}")
        assert player.player_type == "pygame"
        print("✓ Test passed: Fallback to pygame successful")

# Test 3: No player available
print("\n[Test 3] No player available (mpv and pygame both missing)")
print("-" * 70)
with patch("shutil.which", return_value=None):
    original_init = sys.modules["ytm_cli.hybrid_player"].PygamePlayerService.__init__

    def mock_init(self):
        raise ImportError("No pygame")

    sys.modules["ytm_cli.hybrid_player"].PygamePlayerService.__init__ = mock_init

    with patch("builtins.print"):
        from ytm_cli.hybrid_player import CLIHybridPlayerService

        player = CLIHybridPlayerService()
        print(f"✓ Player type: {player.player_type}")
        assert player.player_type == "none"
        assert not player.is_available()
        print("✓ Test passed: Graceful failure when no player available")

    # Restore original
    sys.modules["ytm_cli.hybrid_player"].PygamePlayerService.__init__ = original_init

# Test 4: Pygame player method delegation
print("\n[Test 4] Pygame player method delegation")
print("-" * 70)
with patch("shutil.which", return_value=None):
    mock_pygame_player = MagicMock()
    mock_pygame_player.play = MagicMock(return_value=True)
    mock_pygame_player.is_playing_now = MagicMock(return_value=True)
    mock_pygame_player.pause = MagicMock()
    mock_pygame_player.resume = MagicMock()
    mock_pygame_player.stop = MagicMock()

    with patch("ytm_cli.hybrid_player.PygamePlayerService", return_value=mock_pygame_player):
        with patch("builtins.print"):
            import importlib

            importlib.reload(sys.modules["ytm_cli.hybrid_player"])
            from ytm_cli.hybrid_player import CLIHybridPlayerService

            player = CLIHybridPlayerService()

            # Test play
            result = player.play("test_vid", "Test Song")
            assert result is True
            mock_pygame_player.play.assert_called_once_with("test_vid", "Test Song")
            print("✓ play() delegated correctly")

            # Test is_playing
            result = player.is_playing()
            assert result is True
            mock_pygame_player.is_playing_now.assert_called_once()
            print("✓ is_playing() delegated correctly")

            # Test pause
            player.pause()
            mock_pygame_player.pause.assert_called_once()
            print("✓ pause() delegated correctly")

            # Test resume
            player.resume()
            mock_pygame_player.resume.assert_called_once()
            print("✓ resume() delegated correctly")

            # Test stop
            player.stop()
            mock_pygame_player.stop.assert_called_once()
            print("✓ stop() delegated correctly")

print("\n" + "=" * 70)
print("All pygame fallback tests passed! ✓")
print("=" * 70)
print("\nVerbose log saved to: pygame_test.log\n")
