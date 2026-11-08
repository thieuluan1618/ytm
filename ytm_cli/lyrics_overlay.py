"""Optional macOS desktop lyrics, isolated from the terminal playback loop."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .config import config
from .lyrics_service import LRCParser, get_playback_lyrics


class LyricsOverlay:
    """Send current/next lyric lines to a non-activating AppKit helper over stdin."""

    def __init__(self, get_elapsed):
        self.get_elapsed = get_elapsed
        self._show_next_line = config.getboolean(
            "ui", "lyrics_overlay_show_next_line", fallback=False
        )
        self._lock = threading.Lock()
        self._closed = threading.Event()
        self._worker = None
        self._process = None
        self._enabled = False
        self._paused = False
        self._song = None
        self._generation = 0
        self._lyrics = None
        self._error = None

    def set_track(self, song):
        """Clear stale lines immediately and fetch this track if the overlay is on."""
        with self._lock:
            self._song = song
            self._paused = False
            self._generation += 1
            self._lyrics = None
            if self._enabled:
                self._send(
                    {"visible": song is not None, "current": "Loading synced lyrics…", "next": ""}
                )
                self._load()

    def set_paused(self, paused):
        """Fade while paused; keep fetched lyrics ready for resume."""
        with self._lock:
            self._paused = paused

    def toggle(self):
        """Toggle without waiting for compilation, network requests, or playback IPC."""
        if sys.platform != "darwin":
            return "Desktop lyrics are available on macOS only"
        if not shutil.which("swiftc"):
            return "Desktop lyrics need Apple Command Line Tools: xcode-select --install"
        with self._lock:
            if self._closed.is_set():
                return "Desktop lyrics are closed"
            if self._error:
                return self._error
            self._enabled = not self._enabled
            self._generation += 1
            if self._enabled:
                self._load()
                if self._worker is None:
                    self._worker = threading.Thread(target=self._run, daemon=True)
                    self._worker.start()
                return "Desktop lyrics on · first launch may take a moment"
            self._send({"visible": False})
            return "Desktop lyrics off"

    def _load(self):
        song, generation = self._song, self._generation
        if song is None or self._lyrics is not None:
            return

        def fetch():
            try:
                lyrics = get_playback_lyrics(song) or {}
            except Exception:
                logging.getLogger(__name__).debug("Desktop lyrics lookup failed", exc_info=True)
                lyrics = {}
            with self._lock:
                if generation == self._generation and not self._closed.is_set():
                    self._lyrics = lyrics.get("parsed_lyrics") or []

        threading.Thread(target=fetch, daemon=True).start()

    @staticmethod
    def _helper_path():
        source = Path(__file__).with_name("lyrics_overlay.swift")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        cache = Path.home() / "Library" / "Caches" / "ytm-cli"
        cache.mkdir(parents=True, exist_ok=True)
        binary = cache / f"lyrics-overlay-{digest}"
        if not binary.exists():
            with tempfile.TemporaryDirectory(dir=cache) as temporary:
                output = Path(temporary) / "lyrics-overlay"
                subprocess.run(
                    ["swiftc", str(source), "-o", str(output)],
                    check=True,
                    capture_output=True,
                    timeout=90,
                )
                os.replace(output, binary)
        return binary

    def _send(self, message):
        # All writes and process lifetime changes are serialized by _lock.
        if self._process is not None:
            try:
                self._process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
                self._process.stdin.flush()
            except OSError:
                self._error = "Desktop lyrics helper disconnected"
                self._enabled = False

    def _run(self):
        try:
            binary = self._helper_path()
            with self._lock:
                if self._closed.is_set():
                    return
                self._process = subprocess.Popen(
                    [str(binary)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                )
            previous = None
            while not self._closed.wait(0.15):
                with self._lock:
                    enabled, lyrics, generation = (
                        self._enabled and self._song is not None,
                        self._lyrics,
                        self._generation,
                    )
                    paused = self._paused
                elapsed = self.get_elapsed() if enabled and lyrics else None
                message = {"visible": enabled, "current": "", "next": ""}
                if enabled:
                    if lyrics is None:
                        message["current"] = "Loading synced lyrics…"
                    elif not lyrics:
                        message["current"] = "No synced lyrics available"
                        message["fade_after"] = 3
                    elif elapsed is None:
                        message["current"] = "Waiting for playback…"
                    else:
                        index = LRCParser.get_current_line_index(lyrics, elapsed)
                        message["current"] = lyrics[index][1] if index >= 0 else "♪"
                        if self._show_next_line and index + 1 < len(lyrics):
                            message["next"] = lyrics[index + 1][1]
                    if paused:
                        message["fade_after"] = 0
                with self._lock:
                    if self._closed.is_set():
                        return
                    if generation != self._generation or paused != self._paused:
                        continue
                    if self._process.poll() is not None:
                        raise RuntimeError("Desktop lyrics helper exited")
                    if (generation, message) != previous:
                        self._send(message)
                        previous = (generation, message)
        except Exception:
            logging.getLogger(__name__).debug("Desktop lyrics unavailable", exc_info=True)
            with self._lock:
                self._error = "Desktop lyrics failed · check Apple Command Line Tools"
                self._enabled = False
        finally:
            with self._lock:
                self._stop_helper()

    def _stop_helper(self):
        if self._process is not None:
            try:
                self._process.stdin.close()
            except OSError:
                pass  # A crashed helper may have already closed its end of the pipe.
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.terminate()
                try:
                    self._process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            self._process = None

    def close(self):
        """Hide and stop the helper even if a lyrics request is still in flight."""
        self._closed.set()
        with self._lock:
            self._enabled = False
            self._stop_helper()
