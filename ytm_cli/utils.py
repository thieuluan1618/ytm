"""Utility functions for YTM CLI"""

import os
import signal
import sys
import termios
import tty

# Canonical player control bindings: (icon, key, description).
# Solid text glyphs render consistently across terminal UIs.
PREVIOUS_ICON = "◀◀"
PLAY_ICON = "▶"
PAUSE_ICON = "⏸"
NEXT_ICON = "▶▶"
LYRICS_ICON = "♪"
ADD_ICON = "✚"
DISLIKE_ICON = "▼"
QUIT_ICON = "■"


def player_controls(is_paused: bool = False):
    """Return controls with the play/pause icon showing the next action."""
    return [
        (PREVIOUS_ICON, "b", "previous"),
        (PLAY_ICON if is_paused else PAUSE_ICON, "space", "play" if is_paused else "pause"),
        (NEXT_ICON, "n", "next"),
        (LYRICS_ICON, "l", "lyrics"),
        (ADD_ICON, "a", "save"),
        (DISLIKE_ICON, "d", "dislike"),
        (QUIT_ICON, "q", "quit"),
    ]


def controls_string(is_paused: bool = False, separator: str = "  ") -> str:
    """Render the canonical player controls as a single string."""
    return separator.join(f"{icon} {key}" for icon, key, _ in player_controls(is_paused))


def goodbye_message():
    """Handle Ctrl+C gracefully with a goodbye message"""
    print("\n👋 Goodbye! Thanks for using YTM CLI! 💩 💩 💩")
    sys.exit(0)


def setup_signal_handler():
    """Register the signal handler for graceful exit"""
    signal.signal(signal.SIGINT, lambda signum, frame: goodbye_message())


def clear_screen():
    """Clear the terminal screen in a cross-platform way"""
    os.system("cls" if os.name == "nt" else "clear")


def getch():
    """Get a single character from stdin without pressing enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch
