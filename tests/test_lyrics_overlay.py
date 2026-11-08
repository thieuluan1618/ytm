"""Exercise the overlay's public lifecycle against a real stdin consumer."""

import configparser
import json
import sys
import threading
import time

import pytest

from ytm_cli.lyrics_overlay import LyricsOverlay


def wait_for(predicate):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    assert predicate(), "Overlay did not reach the expected state"


@pytest.fixture
def overlay_output(tmp_path, monkeypatch):
    """Replace only the native renderer; keep real threads and subprocess IPC."""
    output = tmp_path / "messages.jsonl"
    helper = tmp_path / "renderer"
    helper.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"with open({str(output)!r}, 'a') as output:\n"
        "    for line in sys.stdin:\n"
        "        output.write(line)\n"
        "        output.flush()\n"
        "    output.write('EOF\\n')\n"
    )
    helper.chmod(0o755)
    monkeypatch.setattr("ytm_cli.lyrics_overlay.config", configparser.ConfigParser())
    monkeypatch.setattr("ytm_cli.lyrics_overlay.sys.platform", "darwin")
    monkeypatch.setattr("ytm_cli.lyrics_overlay.shutil.which", lambda _: "/usr/bin/swiftc")
    monkeypatch.setattr(LyricsOverlay, "_helper_path", staticmethod(lambda: helper))

    def messages():
        if not output.exists():
            return []
        return [json.loads(line) for line in output.read_text().splitlines() if line != "EOF"]

    return output, messages


@pytest.mark.parametrize("show_next_line", [None, True, False])
def test_synced_lines_seek_toggle_and_cleanup(overlay_output, monkeypatch, show_next_line):
    output, messages = overlay_output
    settings = configparser.ConfigParser()
    if show_next_line is not None:
        settings.read_dict({"ui": {"lyrics_overlay_show_next_line": str(show_next_line)}})
    monkeypatch.setattr("ytm_cli.lyrics_overlay.config", settings)
    position = [0.0]
    monkeypatch.setattr(
        "ytm_cli.lyrics_overlay.get_playback_lyrics",
        lambda _: {"parsed_lyrics": [(1.2, "Đêm nay"), (8.5, "Second"), (15.7, "Last")]},
    )
    overlay = LyricsOverlay(lambda: position[0])

    def has_lines(current, next_line):
        return bool(messages()) and messages()[-1] == {
            "visible": True,
            "current": current,
            "next": next_line if show_next_line is True else "",
        }

    try:
        overlay.set_track({"videoId": "first", "title": "First"})
        assert "on" in overlay.toggle()
        wait_for(lambda: has_lines("♪", "Đêm nay"))
        position[0] = 8.49
        wait_for(lambda: has_lines("Đêm nay", "Second"))
        position[0] = 8.5
        wait_for(lambda: has_lines("Second", "Last"))
        # Frozen player time (pause) must not advance the lyrics using wall time.
        time.sleep(0.35)
        assert has_lines("Second", "Last")
        position[0] = 16
        wait_for(lambda: has_lines("Last", ""))
        position[0] = 2
        wait_for(lambda: has_lines("Đêm nay", "Second"))
        assert overlay.toggle() == "Desktop lyrics off"
        wait_for(lambda: messages()[-1] == {"visible": False})
        # Re-enable before the renderer's next tick: identical lyrics must reappear.
        overlay.toggle()
        wait_for(lambda: has_lines("Đêm nay", "Second"))
    finally:
        overlay.close()
    wait_for(lambda: "EOF" in output.read_text())


def test_track_change_discards_slow_old_lookup(overlay_output, monkeypatch):
    _, messages = overlay_output
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def fetch(song):
        if song["videoId"] == "old":
            started.set()
            release.wait(4)
            finished.set()
            return {"parsed_lyrics": [(0, "Stale lyrics")]}
        if song["videoId"] == "synced":
            return {"parsed_lyrics": [(0, "Current lyric")]}
        return {"plain_lyrics": "No timestamps"}

    monkeypatch.setattr("ytm_cli.lyrics_overlay.get_playback_lyrics", fetch)
    overlay = LyricsOverlay(lambda: 10)
    try:
        overlay.set_track({"videoId": "old"})
        overlay.toggle()
        assert started.wait(2)
        # Loading must not block controls, track changes, or hiding the overlay.
        overlay.toggle()
        overlay.set_track({"videoId": "new"})
        overlay.toggle()
        wait_for(
            lambda: messages() and messages()[-1].get("current") == "No synced lyrics available"
        )
        assert messages()[-1]["fade_after"] == 3
        release.set()
        assert finished.wait(2)
        time.sleep(0.35)
        assert all(message.get("current") != "Stale lyrics" for message in messages())
        overlay.set_track({"videoId": "synced"})
        wait_for(lambda: messages()[-1].get("current") == "Current lyric")
        assert "fade_after" not in messages()[-1]
        overlay.set_track(None)
        wait_for(lambda: messages()[-1].get("visible") is False)
    finally:
        release.set()
        overlay.close()


def test_helper_failure_does_not_escape_to_playback(overlay_output, monkeypatch):
    def fail():
        raise OSError("Compiler unavailable")

    monkeypatch.setattr(LyricsOverlay, "_helper_path", staticmethod(fail))
    overlay = LyricsOverlay(lambda: 0)
    try:
        overlay.toggle()
        wait_for(lambda: "failed" in overlay.toggle())
        overlay.set_track({"videoId": "still-playing"})
    finally:
        overlay.close()


def test_unsupported_platform_never_starts_helper(monkeypatch):
    monkeypatch.setattr("ytm_cli.lyrics_overlay.sys.platform", "linux")
    overlay = LyricsOverlay(lambda: pytest.fail("Playback must not be polled"))
    assert overlay.toggle() == "Desktop lyrics are available on macOS only"
    overlay.close()


def test_overlay_uses_same_lookup_as_terminal(overlay_output, monkeypatch):
    from ytm_cli.player import get_and_display_lyrics

    _, messages = overlay_output
    lookups = []

    def lookup(self, title, artist, album=None, duration=None):
        lookups.append((title, artist, album, duration))
        if album or duration:
            return {"plainLyrics": "Different release"}
        return {"syncedLyrics": "[00:01.00]It's been a long day"}

    monkeypatch.setattr("ytm_cli.lyrics_service.LyricsService.get_lyrics", lookup)
    displayed = []
    monkeypatch.setattr(
        "ytm_cli.player.display_lyrics_with_curses", lambda lyrics, *args: displayed.append(lyrics)
    )
    song = {
        "videoId": "test",
        "title": "See You Again (feat. Charlie Puth)",
        "artists": [{"name": "Wiz Khalifa"}],
        "album": {"name": "Video release"},
        "duration_seconds": 230,
    }
    assert get_and_display_lyrics("test", song["title"], artist="Wiz Khalifa")
    overlay = LyricsOverlay(lambda: 2)
    try:
        overlay.set_track(song)
        overlay.toggle()
        wait_for(lambda: messages() and messages()[-1].get("current") == "It's been a long day")
        assert lookups == [lookups[0], lookups[0]]
        assert lookups[0] == (song["title"], "Wiz Khalifa", "", 0)
        assert displayed[0]["parsed_lyrics"] == [(1.0, "It's been a long day")]
    finally:
        overlay.close()


def test_pause_fades_and_resume_restores_same_line(overlay_output, monkeypatch):
    _, messages = overlay_output
    monkeypatch.setattr(
        "ytm_cli.lyrics_overlay.get_playback_lyrics",
        lambda _: {"parsed_lyrics": [(0, "Current line")]},
    )
    overlay = LyricsOverlay(lambda: 2)
    try:
        overlay.set_track({"videoId": "song"})
        overlay.toggle()
        wait_for(lambda: messages() and messages()[-1].get("current") == "Current line")
        overlay.set_paused(True)
        wait_for(lambda: messages()[-1].get("fade_after") == 0)
        count = len(messages())
        time.sleep(0.5)
        assert len(messages()) == count  # Do not keep restarting the fade.
        overlay.set_paused(False)
        wait_for(lambda: "fade_after" not in messages()[-1])
        assert messages()[-1]["current"] == "Current line"
        overlay.set_paused(True)
        wait_for(lambda: messages()[-1].get("fade_after") == 0)
        overlay.set_track({"videoId": "next-song"})
        wait_for(
            lambda: (
                messages()[-1].get("current") == "Current line"
                and "fade_after" not in messages()[-1]
            )
        )
    finally:
        overlay.close()
