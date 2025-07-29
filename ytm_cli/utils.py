"""Utility functions for YTM CLI"""

import os
import signal
import sys
import termios
import tty


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
