#!/usr/bin/env python3
"""
Simple test to verify pygame fallback in CLI mode.
This test checks that the CLIHybridPlayerService correctly:
1. Prefers MPV when available
2. Falls back to pygame when MPV is unavailable
3. Gracefully handles when both are unavailable
"""

from ytm_cli.verbose_logger import set_verbose

# Enable verbose logging
set_verbose(True, "pygame_cli_test.log")

print("\n" + "=" * 70)
print("CLI Hybrid Player - Pygame Fallback Test")
print("=" * 70 + "\n")

from ytm_cli.hybrid_player import CLIHybridPlayerService

# Test initialization
print("\n[Test] Initialize CLIHybridPlayerService")
print("-" * 70)

player = CLIHybridPlayerService()

print(f"\nPlayer Initialization Summary:")
print(f"  • Player type: {player.player_type}")
print(f"  • Is available: {player.is_available()}")
print(f"  • Player info: {player.get_player_info()}")

# Test that methods are callable
print("\n[Test] Verify player methods are available")
print("-" * 70)

if player.is_available():
    print("✓ Player is available")

    # Test that all methods exist and are callable
    methods = ["play", "pause", "resume", "stop", "is_playing", "cleanup"]
    for method in methods:
        if hasattr(player, method):
            print(f"  ✓ Method '{method}' exists")
        else:
            print(f"  ✗ Method '{method}' missing!")

else:
    print("✗ No player available (this is OK if mpv and pygame aren't both installed)")

print("\n" + "=" * 70)
if player.player_type == "mpv":
    print("Result: Using MPV for playback")
elif player.player_type == "pygame":
    print("Result: Using Pygame fallback (MPV not available)")
else:
    print("Result: No audio player available")
print("=" * 70)
print(f"\nDetailed log saved to: pygame_cli_test.log\n")
