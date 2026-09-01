#!/usr/bin/env python3
"""Quick test of the rich progress bar."""

from rich.console import Console

from ytm_cli.rich_ui import create_player_layout

console = Console()

# Test at different progress points
test_cases = [
    (0, 180, "Start"),
    (54, 180, "30%"),
    (90, 180, "50%"),
    (144, 180, "80%"),
    (179, 180, "End"),
]

for elapsed, duration, label in test_cases:
    print(f"\n{'=' * 60}")
    print(f"{label}: {elapsed}s / {duration}s")
    print("=" * 60)

    layout = create_player_layout(
        song_title="Test Song",
        artist="Test Artist",
        is_paused=False,
        track_idx=1,
        track_total=5,
        elapsed=elapsed,
        duration=duration,
        next_title="Next Song",
        next_artist="Next Artist",
    )

    console.print(layout)
    print()

print("\n✅ Progress bar test complete!")
