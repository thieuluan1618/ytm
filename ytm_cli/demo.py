"""Demo mode — deterministic UI for screenshot pipeline.

No network, no audio, no mpv. Replaces the player and spectrum analyzer
with stand-ins so vhs / asciinema can capture stable terminal frames.
"""

import math
import time

DEMO_PLAYLIST = [
    {
        "videoId": "demo_synthwave_01",
        "title": "Neon Cruise",
        "artists": [{"name": "Synthwave Demo Band"}],
    },
    {
        "videoId": "demo_lofi_02",
        "title": "Rainy Afternoon Lo-Fi",
        "artists": [{"name": "ChillCat"}],
    },
    {
        "videoId": "demo_bass_03",
        "title": "Sub-Bass Anthem",
        "artists": [{"name": "DJ Fixture"}],
    },
    {
        "videoId": "demo_treble_04",
        "title": "Crystal Bells",
        "artists": [{"name": "TrebleFest"}],
    },
]


class DemoPlayer:
    """Stand-in for CLIHybridPlayerService — no real audio backend."""

    def __init__(self):
        self.player_type = "demo"
        self.socket_path = None
        self._playing = False
        self._paused = False
        self._start_time = 0.0
        self._pause_at = 0.0
        self._duration = 180.0  # 3 min per fake track

    def is_available(self) -> bool:
        return True

    def play(self, video_id: str, title: str = "") -> bool:
        self._start_time = time.time()
        self._playing = True
        self._paused = False
        return True

    def pause(self) -> None:
        if self._playing and not self._paused:
            self._pause_at = time.time()
            self._paused = True

    def resume(self) -> None:
        if self._paused:
            self._start_time += time.time() - self._pause_at
            self._paused = False

    def stop(self) -> None:
        self._playing = False
        self._paused = False

    def is_playing(self) -> bool:
        if not self._playing:
            return False
        if self._paused:
            return True
        return (time.time() - self._start_time) < self._duration

    def cleanup(self) -> None:
        self.stop()


class DemoSpectrum:
    """Synthetic but visually believable band data — replaces SpectrumAnalyzer."""

    def __init__(self, n_bands: int = 24):
        self.n_bands = n_bands
        self._t0 = time.time()
        self._has_data = True

    @staticmethod
    def available() -> bool:
        return True

    def start(self, source_url: str) -> bool:
        self._t0 = time.time()
        self._has_data = True
        return True

    def stop(self) -> None:
        self._has_data = False

    def get_bands(self):
        if not self._has_data:
            return None
        t = time.time() - self._t0
        bands = []
        for i in range(self.n_bands):
            # Bass-heavy pulse + treble shimmer + slow drift, all bounded 0..1.
            pulse = max(0.0, math.sin(t * 2.0 - i * 0.18)) ** 1.5
            bass_weight = max(0.0, 1.0 - i / 7.0)
            shimmer = 0.25 * abs(math.sin(t * 5.0 + i * 0.55))
            drift = 0.15 * (0.5 + 0.5 * math.sin(t * 0.25 + i * 0.1))
            level = pulse * (0.5 + bass_weight) + shimmer + drift
            bands.append(min(1.0, max(0.0, level)))
        return bands


def run_demo() -> None:
    """Boot the player with the demo fixture — entry point for `ytm-cli --demo`."""
    from .player import play_music_with_controls

    play_music_with_controls(DEMO_PLAYLIST, demo=True)
