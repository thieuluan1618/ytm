#!/usr/bin/env python3
"""Interactive demo of the rich-based player with keyboard controls."""

import time

from rich.console import Console
from rich.live import Live

from ytm_cli.rich_ui import create_player_layout, getch_nonblocking
from ytm_cli.utils import NEXT_ICON, PAUSE_ICON, PLAY_ICON, PREVIOUS_ICON


def interactive_demo():
    """Demo player with keyboard controls."""
    console = Console()

    # State
    is_paused = False
    elapsed = 0.0
    duration = 180.0
    track_idx = 1
    track_total = 5
    toast_msg = None
    toast_detail = None
    toast_expire = 0

    console.print("[cyan bold]🎵 Rich-based Player Demo[/cyan bold]")
    console.print("[dim]Controls: Space=pause, N=next, B=prev, Q=quit[/dim]\n")
    time.sleep(2)

    layout = create_player_layout(
        song_title="Neon Cruise",
        artist="Synthwave Demo Band",
        is_paused=is_paused,
        track_idx=track_idx,
        track_total=track_total,
        elapsed=elapsed,
        duration=duration,
        toast_msg=toast_msg,
        toast_detail=toast_detail,
        next_title="Digital Dreams",
        next_artist="Retrowave Collective",
    )

    with Live(layout, console=console, refresh_per_second=10, screen=True) as live:
        last_update = time.time()

        while True:
            now = time.time()

            # Update elapsed time if playing
            if not is_paused and elapsed < duration:
                elapsed += now - last_update
                if elapsed > duration:
                    elapsed = duration

            last_update = now

            # Clear expired toast
            if toast_msg and time.time() >= toast_expire:
                toast_msg = None
                toast_detail = None

            # Check for keyboard input (non-blocking)
            key = getch_nonblocking(0.01)
            if key:
                if key == " ":
                    is_paused = not is_paused
                    toast_msg = f"{PAUSE_ICON} Paused" if is_paused else f"{PLAY_ICON} Playing"
                    toast_expire = time.time() + 1.5
                elif key == "n":
                    track_idx = min(track_idx + 1, track_total)
                    elapsed = 0
                    toast_msg = f"{NEXT_ICON} Next"
                    toast_expire = time.time() + 1.5
                elif key == "b":
                    track_idx = max(track_idx - 1, 1)
                    elapsed = 0
                    toast_msg = f"{PREVIOUS_ICON} Previous"
                    toast_expire = time.time() + 1.5
                elif key == "a":
                    toast_msg = "Added · Neon Cruise · Synthwave Demo Band"
                    toast_detail = "Saved to playlist · Favorites"
                    toast_expire = time.time() + 3.5
                elif key == "d":
                    toast_msg = "Disliked · Neon Cruise · Synthwave Demo Band"
                    toast_detail = "Hidden from future searches and radio playlists"
                    toast_expire = time.time() + 3.5
                elif key == "q" or key == "\x03":  # q or Ctrl+C
                    break

            # Update layout
            layout = create_player_layout(
                song_title="Neon Cruise",
                artist="Synthwave Demo Band",
                is_paused=is_paused,
                track_idx=track_idx,
                track_total=track_total,
                elapsed=elapsed,
                duration=duration,
                toast_msg=toast_msg,
                toast_detail=toast_detail,
                next_title="Digital Dreams",
                next_artist="Retrowave Collective",
            )

            live.update(layout)

            # End of track
            if elapsed >= duration:
                break

    console.print("\n[green]✅ Demo complete![/green]")


if __name__ == "__main__":
    try:
        interactive_demo()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
