"""Tests for ytm_cli.spectrum.SpectrumAnalyzer.

These cover the parts that don't require an ffmpeg subprocess: band-bin
construction, availability detection, start/stop guard behaviour, and
get_bands gating on _has_data.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ytm_cli.spectrum import SpectrumAnalyzer


class TestInitAndBandBins:
    def test_default_n_bands(self):
        sa = SpectrumAnalyzer()
        assert sa.n_bands == 24
        assert sa._bands.shape == (24,)
        assert sa._bands.dtype == np.float32
        assert np.all(sa._bands == 0.0)

    def test_custom_n_bands(self):
        sa = SpectrumAnalyzer(n_bands=8)
        assert sa.n_bands == 8
        assert sa._bands.shape == (8,)
        assert len(sa._band_slices) == 8

    def test_band_slices_are_monotonic_and_non_empty(self):
        sa = SpectrumAnalyzer(n_bands=12)
        last_hi = -1
        for lo, hi in sa._band_slices:
            assert hi > lo, "every band must contain at least one bin"
            assert lo >= last_hi or lo == 0, "bands should be non-decreasing"
            last_hi = hi

    def test_window_matches_chunk_size(self):
        sa = SpectrumAnalyzer()
        assert sa._window.shape == (SpectrumAnalyzer.CHUNK,)
        assert sa._window.dtype == np.float32
        # Hann window peaks near the center.
        assert sa._window.max() == pytest.approx(1.0, rel=1e-2)

    def test_initial_state_flags(self):
        sa = SpectrumAnalyzer()
        assert sa._running is False
        assert sa._has_data is False
        assert sa._proc is None
        assert sa._thread is None


class TestAvailable:
    def test_available_returns_true_when_ffmpeg_in_path(self):
        with patch("ytm_cli.spectrum.shutil.which", return_value="/usr/bin/ffmpeg"):
            assert SpectrumAnalyzer.available() is True

    def test_available_returns_false_when_ffmpeg_missing(self):
        with patch("ytm_cli.spectrum.shutil.which", return_value=None):
            assert SpectrumAnalyzer.available() is False


class TestGetBands:
    def test_get_bands_returns_none_before_any_data(self):
        sa = SpectrumAnalyzer()
        assert sa.get_bands() is None

    def test_get_bands_returns_list_after_data_flag(self):
        sa = SpectrumAnalyzer(n_bands=4)
        sa._bands = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        sa._has_data = True

        bands = sa.get_bands()
        assert isinstance(bands, list)
        assert len(bands) == 4
        for got, want in zip(bands, [0.1, 0.2, 0.3, 0.4], strict=True):
            assert got == pytest.approx(want, rel=1e-5)


class TestStart:
    def test_start_returns_false_when_ffmpeg_unavailable(self):
        sa = SpectrumAnalyzer()
        with patch.object(SpectrumAnalyzer, "available", return_value=False):
            assert sa.start("http://example/audio") is False
        assert sa._running is False

    def test_start_returns_false_with_empty_url(self):
        sa = SpectrumAnalyzer()
        with patch.object(SpectrumAnalyzer, "available", return_value=True):
            assert sa.start("") is False

    def test_start_returns_false_when_popen_raises_oserror(self):
        sa = SpectrumAnalyzer()
        with (
            patch.object(SpectrumAnalyzer, "available", return_value=True),
            patch("ytm_cli.spectrum.subprocess.Popen", side_effect=OSError("boom")),
        ):
            assert sa.start("http://example/audio") is False
        assert sa._running is False

    def test_start_spawns_ffmpeg_and_marks_running(self):
        sa = SpectrumAnalyzer()
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        # Reader will hit `len(data) < chunk_bytes` immediately and exit.
        fake_proc.stdout.read.return_value = b""

        with (
            patch.object(SpectrumAnalyzer, "available", return_value=True),
            patch("ytm_cli.spectrum.subprocess.Popen", return_value=fake_proc) as mock_popen,
        ):
            ok = sa.start("http://example/audio")

        assert ok is True
        assert sa._proc is fake_proc
        assert sa._thread is not None
        # Ensure we asked ffmpeg for s16le mono at the analyzer's sample rate.
        cmd = mock_popen.call_args.args[0]
        assert cmd[0] == "ffmpeg"
        assert "-f" in cmd and cmd[cmd.index("-f") + 1] == "s16le"
        assert "-ac" in cmd and cmd[cmd.index("-ac") + 1] == "1"
        assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == str(SpectrumAnalyzer.SR)


class TestStop:
    def test_stop_when_never_started_is_safe(self):
        sa = SpectrumAnalyzer(n_bands=4)
        sa._bands = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
        sa._has_data = True

        sa.stop()

        assert sa._running is False
        assert sa._proc is None
        assert sa._thread is None
        assert sa._has_data is False
        assert np.all(sa._bands == 0.0)

    def test_stop_terminates_running_process(self):
        sa = SpectrumAnalyzer()
        fake_proc = MagicMock()
        fake_proc.wait.return_value = 0
        sa._proc = fake_proc
        sa._running = True

        sa.stop()

        fake_proc.terminate.assert_called_once()
        fake_proc.wait.assert_called()
        assert sa._proc is None
        assert sa._running is False

    def test_stop_kills_process_on_terminate_timeout(self):
        sa = SpectrumAnalyzer()
        fake_proc = MagicMock()
        # First wait raises TimeoutExpired, then kill+wait succeed.
        from subprocess import TimeoutExpired

        fake_proc.wait.side_effect = [TimeoutExpired(cmd="ffmpeg", timeout=1), 0]
        sa._proc = fake_proc
        sa._running = True

        sa.stop()

        fake_proc.terminate.assert_called_once()
        fake_proc.kill.assert_called_once()
        assert sa._proc is None
