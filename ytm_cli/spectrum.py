"""Real-time audio spectrum analyzer.

Spawns an ffmpeg sidecar that decodes the resolved media URL to raw PCM,
runs an FFT in a background thread, and exposes log-spaced frequency bands
for the visualizer. No microphone capture — ffmpeg pulls the same media URL
that mpv is already streaming.
"""

import shutil
import subprocess
import threading

import numpy as np


class SpectrumAnalyzer:
    SR = 22050  # Nyquist 11kHz covers most musical content
    CHUNK = 2048  # ~93ms per FFT frame, ~11Hz bin resolution

    BAND_LO_HZ = 50.0
    BAND_HI_HZ = 10500.0

    def __init__(self, n_bands: int = 24):
        self.n_bands = n_bands
        self._bands = np.zeros(n_bands, dtype=np.float32)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._has_data = False
        self._build_band_bins()

    def _build_band_bins(self) -> None:
        bin_freqs = np.fft.rfftfreq(self.CHUNK, 1.0 / self.SR)
        edges = np.geomspace(self.BAND_LO_HZ, self.BAND_HI_HZ, self.n_bands + 1)
        slices = []
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            i_lo = int(np.searchsorted(bin_freqs, lo, side="left"))
            i_hi = int(np.searchsorted(bin_freqs, hi, side="right"))
            if i_hi <= i_lo:
                i_hi = i_lo + 1
            slices.append((i_lo, i_hi))
        self._band_slices = slices
        self._window = np.hanning(self.CHUNK).astype(np.float32)

    @staticmethod
    def available() -> bool:
        return bool(shutil.which("ffmpeg"))

    def start(self, source_url: str) -> bool:
        if not self.available() or not source_url:
            return False
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            source_url,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(self.SR),
            "-f",
            "s16le",
            "-",
        ]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except OSError:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        return True

    def _reader(self) -> None:
        chunk_bytes = self.CHUNK * 2  # int16 little-endian
        prev = self._bands.copy()
        try:
            while self._running and self._proc is not None and self._proc.poll() is None:
                if self._proc.stdout is None:
                    break
                data = self._proc.stdout.read(chunk_bytes)
                if not data or len(data) < chunk_bytes:
                    break
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                samples = samples * self._window
                spec = np.abs(np.fft.rfft(samples)).astype(np.float32)

                new = np.empty(self.n_bands, dtype=np.float32)
                for i, (lo, hi) in enumerate(self._band_slices):
                    new[i] = spec[lo:hi].mean() if hi > lo else 0.0

                # Compress dynamic range — bass dominates linear FFT mag otherwise.
                new = np.log1p(new * 40.0) / np.log(41.0)
                np.clip(new, 0.0, 1.0, out=new)

                # Asymmetric smoothing: snappy attack, gentler release.
                rise_mask = new > prev
                prev = np.where(
                    rise_mask,
                    prev * 0.3 + new * 0.7,
                    prev * 0.75 + new * 0.25,
                )

                with self._lock:
                    self._bands = prev.copy()
                    self._has_data = True
        except (OSError, ValueError):
            pass
        finally:
            self._running = False

    def get_bands(self) -> list[float] | None:
        with self._lock:
            if not self._has_data:
                return None
            return self._bands.tolist()

    def stop(self) -> None:
        self._running = False
        if self._proc is not None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    try:
                        self._proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
            except OSError:
                pass
            self._proc = None
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        with self._lock:
            self._bands.fill(0.0)
            self._has_data = False
