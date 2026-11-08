"""Real-time spectrum of the audio mpv is playing.

mpv measures the band levels itself, inside its audio filter chain, so the bars
follow pause, seek, and buffering exactly. There is no microphone capture and no
second download, and the sound is unchanged: the band channels exist only for
analysis and are dropped before output.
"""

import math
import time
from collections import deque
from collections.abc import Callable
from itertools import pairwise

BAND_COUNT = 24
_BAND_LO_HZ = 50.0
_BAND_HI_HZ = 10500.0
_ANALYSIS_FRAME_SAMPLES = 4800  # About 100ms, so UI ticks see most of the audio.

# Bars span this range below the song's recent loudest band, so quiet and heavily
# compressed masters both move instead of sitting low or pinned at full height.
_RANGE_DB = 18.0
_REFERENCE_DECAY_DB = 0.3  # Per update, so a quiet passage slowly regains height.
_QUIETEST_REFERENCE_DB = -30.0  # Keeps near-silence from being amplified into bars.
_TREBLE_TILT_DB = 6.0  # Music loses energy with frequency; lift the top bands to match.

_FIRST_BAND_CHANNEL = 3  # astats counts from 1, and channels 1-2 are the stereo music.

# Measured on macOS CoreAudio: mpv analyses audio about this long before it is heard.
_DISPLAY_DELAY_SECONDS = 0.25

_RISE = 0.7
_FALL = 0.3


def mpv_audio_filter() -> str:
    """Return the --af-append value that adds per-band levels to mpv's metadata."""
    ratio = (_BAND_HI_HZ / _BAND_LO_HZ) ** (1 / BAND_COUNT)
    edges = [_BAND_LO_HZ * ratio**i for i in range(BAND_COUNT + 1)]
    branches = "".join(f"[b{i}]" for i in range(BAND_COUNT))
    bandpasses = ";".join(
        f"[b{i}]bandpass=f={math.sqrt(low * high):.1f}:width_type=h:w={high - low:.1f}[c{i}]"
        for i, (low, high) in enumerate(pairwise(edges))
    )
    merged = "".join(f"[c{i}]" for i in range(BAND_COUNT))
    graph = (
        "aformat=channel_layouts=stereo,asplit=2[music][mono];"
        f"[mono]pan=mono|c0=0.5*c0+0.5*c1,asplit={BAND_COUNT}{branches};{bandpasses};"
        f"[music]{merged}amerge=inputs={BAND_COUNT + 1},"
        f"asetnsamples=n={_ANALYSIS_FRAME_SAMPLES}:p=0,"
        "astats=metadata=1:reset=1:measure_perchannel=RMS_level+Peak_level:measure_overall=none,"
        "pan=stereo|c0=c0|c1=c1"
    )
    # mpv's %length% quoting keeps the graph's brackets out of its option parser.
    return f"@vstats:lavfi=graph=%{len(graph.encode())}%{graph}"


def _band_db_from_metadata(metadata: dict) -> list[float] | None:
    """Read mpv's per-band RMS levels in dB, with the treble tilt applied."""
    readings = []
    for band in range(BAND_COUNT):
        try:
            db = float(metadata[f"lavfi.astats.{_FIRST_BAND_CHANNEL + band}.RMS_level"])
        except (KeyError, TypeError, ValueError):
            return None
        tilt = _TREBLE_TILT_DB * band / (BAND_COUNT - 1)
        readings.append(-math.inf if math.isnan(db) else db + tilt)
    return readings


class MpvSpectrum:
    """Turn mpv's band metadata into smoothed bars timed to what is audible."""

    def __init__(self, read_metadata: Callable[[], dict | None]):
        self._read_metadata = read_metadata
        self._pending: deque[tuple[float, list[float]]] = deque()
        self._bars: list[float] | None = None
        self._reference_db = _QUIETEST_REFERENCE_DB

    def get_bands(self) -> list[float] | None:
        """Return the current bars, or None while no audio is playing."""
        metadata = self._read_metadata()
        readings = _band_db_from_metadata(metadata) if metadata else None
        if readings is None:
            self.stop()
            return None

        now = time.monotonic()
        self._pending.append((now, readings))

        def delay_error(index):
            return abs(now - self._pending[index][0] - _DISPLAY_DELAY_SECONDS)

        while len(self._pending) > 1 and delay_error(1) <= delay_error(0):
            self._pending.popleft()
        due = self._pending[0][1]

        self._reference_db = max(
            max(due), self._reference_db - _REFERENCE_DECAY_DB, _QUIETEST_REFERENCE_DB
        )
        floor_db = self._reference_db - _RANGE_DB
        levels = [min(1.0, max(0.0, (db - floor_db) / _RANGE_DB)) for db in due]

        if self._bars is None:
            self._bars = levels
        else:
            self._bars = [
                old + (new - old) * (_RISE if new > old else _FALL)
                for old, new in zip(self._bars, levels, strict=True)
            ]
        return list(self._bars)

    def stop(self) -> None:
        """Forget buffered readings and loudness, e.g. between tracks."""
        self._pending.clear()
        self._bars = None
        self._reference_db = _QUIETEST_REFERENCE_DB
