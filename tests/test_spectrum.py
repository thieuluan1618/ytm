"""Tests for the visualizer's mpv-driven spectrum."""

import re
from unittest.mock import patch

import pytest

from ytm_cli.player import get_mpv_audio_levels, read_mpv_band_metadata
from ytm_cli.spectrum import BAND_COUNT, MpvSpectrum, mpv_audio_filter

FIRST_BAND_CHANNEL = 3


def metadata(db="-27"):
    """Build mpv's af-metadata with one value for every band, or a per-band list."""
    values = db if isinstance(db, list) else [db] * BAND_COUNT
    return {
        f"lavfi.astats.{FIRST_BAND_CHANNEL + band}.RMS_level": value
        for band, value in enumerate(values)
    }


def spectrum_reading(*readings):
    """Create a spectrum that returns each reading from mpv in turn."""
    source = iter(readings)
    return MpvSpectrum(lambda: next(source))


class TestMpvAudioFilter:
    def test_quoted_length_matches_the_graph(self):
        match = re.fullmatch(r"@vstats:lavfi=graph=%(\d+)%(.+)", mpv_audio_filter())

        assert match is not None
        assert int(match.group(1)) == len(match.group(2).encode())

    def test_measures_every_band_and_outputs_only_the_music(self):
        graph = mpv_audio_filter()

        assert graph.count("bandpass=") == BAND_COUNT
        assert f"amerge=inputs={BAND_COUNT + 1}" in graph
        assert graph.endswith("pan=stereo|c0=c0|c1=c1")


class TestLevels:
    @pytest.mark.parametrize("master_level", ["0", "-12", "-24"])
    def test_loudest_band_fills_the_bar_at_any_master_level(self, master_level):
        assert spectrum_reading(metadata(master_level)).get_bands()[-1] == 1.0

    def test_near_silence_is_not_amplified(self):
        assert spectrum_reading(metadata("-90")).get_bands() == [0.0] * BAND_COUNT

    def test_quiet_passage_slowly_regains_height(self):
        readings = [metadata("-6")] + [metadata("-18")] * 4
        with (
            patch("ytm_cli.spectrum._DISPLAY_DELAY_SECONDS", 0.0),
            patch("ytm_cli.spectrum._FALL", 1.0),
            patch("ytm_cli.spectrum._RISE", 1.0),
            patch("ytm_cli.spectrum.time.monotonic", side_effect=[1.0, 2.0, 3.0, 4.0, 5.0]),
        ):
            spectrum = spectrum_reading(*readings)
            bars = [spectrum.get_bands() for _ in readings]

        assert bars[4][0] > bars[1][0]

    @pytest.mark.parametrize("silence", ["-inf", "nan"])
    def test_silence_reads_as_empty(self, silence):
        assert spectrum_reading(metadata(silence)).get_bands() == [0.0] * BAND_COUNT

    def test_treble_is_lifted_to_match_bass(self):
        bands = spectrum_reading(metadata()).get_bands()

        assert bands[-1] > bands[0]

    def test_each_band_keeps_its_own_level(self):
        values = ["-90"] * BAND_COUNT
        values[5] = "-20"

        bands = spectrum_reading(metadata(values)).get_bands()

        assert bands[5] > 0.5
        assert bands[4] == 0.0

    def test_incomplete_metadata_is_not_drawn(self):
        partial = metadata()
        del partial[f"lavfi.astats.{FIRST_BAND_CHANNEL}.RMS_level"]

        assert spectrum_reading(partial).get_bands() is None

    @pytest.mark.parametrize("nothing_playing", [None, {}])
    def test_no_audio_gives_no_bars(self, nothing_playing):
        assert spectrum_reading(nothing_playing).get_bands() is None


class TestTiming:
    def run_at(self, spectrum, *times):
        with patch("ytm_cli.spectrum.time.monotonic", side_effect=times):
            return [spectrum.get_bands() for _ in times]

    def test_shows_the_reading_that_is_audible_now(self):
        spectrum = spectrum_reading(metadata("-90"), metadata("-12"), metadata("-12"))

        bars = self.run_at(spectrum, 10.0, 10.15, 10.30)

        # 0.25s behind at 10.30 is the 10.0 reading, nearest of 0.30s and 0.15s old.
        assert bars[2][0] == 0.0

    def test_catches_up_once_the_delay_has_passed(self):
        spectrum = spectrum_reading(*[metadata("-90"), metadata("-12"), metadata("-12")] * 2)

        bars = self.run_at(spectrum, 10.0, 10.15, 10.30, 10.45, 10.60, 10.75)

        assert bars[-1][0] > bars[2][0]

    def test_bars_rise_faster_than_they_fall(self):
        with patch("ytm_cli.spectrum._DISPLAY_DELAY_SECONDS", 0.0):
            rising = spectrum_reading(metadata("-90"), metadata("-12"))
            rising_bars = self.run_at(rising, 1.0, 2.0)
            falling = spectrum_reading(metadata("-12"), metadata("-90"))
            falling_bars = self.run_at(falling, 1.0, 2.0)

        target = falling_bars[0][0]
        assert rising_bars[1][0] == pytest.approx(target * 0.7)  # Rises 70% of the way.
        assert falling_bars[1][0] == pytest.approx(target * 0.7)  # Falls only 30% of the way.

    def test_stopped_audio_forgets_earlier_bars(self):
        with patch("ytm_cli.spectrum._DISPLAY_DELAY_SECONDS", 0.0):
            spectrum = spectrum_reading(metadata("-12"), None, metadata("-90"))
            bars = self.run_at(spectrum, 1.0, 2.0, 3.0)

        assert bars[1] is None
        assert bars[2][0] == 0.0  # Not smoothed against the pre-pause level.

    def test_stop_forgets_earlier_bars(self):
        with patch("ytm_cli.spectrum._DISPLAY_DELAY_SECONDS", 0.0):
            spectrum = spectrum_reading(metadata("-12"), metadata("-90"))
            with patch("ytm_cli.spectrum.time.monotonic", return_value=1.0):
                spectrum.get_bands()
                spectrum.stop()
                bars = spectrum.get_bands()

        assert bars[0] == 0.0


class TestMpvReaders:
    def test_reads_metadata_while_audio_plays(self):
        with patch("ytm_cli.player._mpv_ipc", side_effect=[False, {"key": "value"}]):
            assert read_mpv_band_metadata("/tmp/mpv.sock") == {"key": "value"}

    @pytest.mark.parametrize("idle", [True, None])
    def test_reports_nothing_unless_mpv_is_playing(self, idle):
        with patch("ytm_cli.player._mpv_ipc", return_value=idle) as ipc:
            assert read_mpv_band_metadata("/tmp/mpv.sock") is None

        ipc.assert_called_once()  # Frozen metadata from before a pause is never read.

    def test_stereo_levels_ignore_the_analysis_channels(self):
        readings = {
            "lavfi.astats.1.RMS_level": "-30",
            "lavfi.astats.2.RMS_level": "-30",
            "lavfi.astats.1.Peak_level": "-12",
            "lavfi.astats.2.Peak_level": "-6",
            "lavfi.astats.3.RMS_level": "0",
        }
        with patch("ytm_cli.player._mpv_ipc", return_value=readings):
            levels = get_mpv_audio_levels("/tmp/mpv.sock")

        assert levels["rms"] == pytest.approx(0.5)
        assert levels["left"] == levels["right"] == pytest.approx(0.5)
        assert levels["peak"] == pytest.approx(0.9)
