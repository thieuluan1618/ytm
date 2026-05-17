"""User interface components for YTM CLI"""

import curses
import math
import os
import sys
import time
from collections import deque
from curses import wrapper

from .playlists import playlist_manager


def display_lyrics_with_curses(
    lyrics_data, title, artist=None, socket_path=None, get_mpv_time_position_func=None
):
    """Display lyrics using curses with live highlighting"""

    def lyrics_ui(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()

        curses.init_pair(1, curses.COLOR_YELLOW, -1)  # accent
        curses.init_pair(2, curses.COLOR_WHITE, -1)  # future lines
        curses.init_pair(3, curses.COLOR_WHITE, -1)  # past lines (dimmed via A_DIM)
        curses.init_pair(4, curses.COLOR_WHITE, -1)  # separator
        curses.init_pair(5, curses.COLOR_YELLOW, -1)  # active line accent marker

        accent = curses.color_pair(1) | curses.A_BOLD
        accent_n = curses.color_pair(1)
        future_color = curses.color_pair(2) | curses.A_DIM
        past_color = curses.color_pair(3) | curses.A_DIM
        active_color = curses.color_pair(2) | curses.A_BOLD
        sep_color = curses.color_pair(4) | curses.A_DIM
        border_color = curses.color_pair(4) | curses.A_DIM

        timestamped_lyrics = []

        if isinstance(lyrics_data, dict):
            if lyrics_data.get("parsed_lyrics"):
                timestamped_lyrics = lyrics_data["parsed_lyrics"]
                lyrics_text = lyrics_data.get("synced_lyrics", "") or lyrics_data.get(
                    "plain_lyrics", ""
                )
            else:
                lyrics_text = lyrics_data.get("plain_lyrics", "") or lyrics_data.get(
                    "synced_lyrics", ""
                )
        else:
            lyrics_text = lyrics_data or ""

        if timestamped_lyrics:
            lines = [text for _, text in timestamped_lyrics]
        else:
            lines = [line.strip() for line in lyrics_text.split("\n")]

        max_y, max_x = stdscr.getmaxyx()
        cw = min(max_x - 4, 70)
        lm = (max_x - cw) // 2

        wrapped_lines = []
        timestamp_map = {}
        # Map each wrapped line index → original lyric index, so all sub-lines
        # of a wrapped lyric share the same active/past/future state.
        wrapped_to_orig = {}

        for orig_idx, line in enumerate(lines):
            if len(line) <= cw - 6:
                wrapped_lines.append(line)
                wrapped_to_orig[len(wrapped_lines) - 1] = orig_idx
                if timestamped_lyrics and orig_idx < len(timestamped_lyrics):
                    timestamp_map[len(wrapped_lines) - 1] = timestamped_lyrics[orig_idx][0]
            else:
                words = line.split()
                current_line = ""
                ts = (
                    timestamped_lyrics[orig_idx][0]
                    if timestamped_lyrics and orig_idx < len(timestamped_lyrics)
                    else None
                )
                first_sub = True
                for word in words:
                    if len(current_line + " " + word) <= cw - 6:
                        current_line += " " + word if current_line else word
                    else:
                        wrapped_lines.append(current_line)
                        wrapped_to_orig[len(wrapped_lines) - 1] = orig_idx
                        if ts is not None and first_sub:
                            timestamp_map[len(wrapped_lines) - 1] = ts
                            first_sub = False
                        current_line = word
                if current_line:
                    wrapped_lines.append(current_line)
                    wrapped_to_orig[len(wrapped_lines) - 1] = orig_idx
                    if ts is not None and first_sub:
                        timestamp_map[len(wrapped_lines) - 1] = ts

        lines = wrapped_lines
        sorted_ts = sorted(timestamp_map.items(), key=lambda x: x[1])
        scroll_pos = 0
        manual_scroll = False
        content_height = max_y - 4

        while True:
            stdscr.erase()

            current_highlighted_line = -1
            active_orig_idx = -1
            current_time = 0
            if socket_path and get_mpv_time_position_func:
                pos = get_mpv_time_position_func(socket_path)
                if pos is not None:
                    current_time = pos

                if timestamped_lyrics and current_time > 0:
                    for line_idx, ts in sorted_ts:
                        if current_time >= ts:
                            current_highlighted_line = line_idx
                        else:
                            break
                    if current_highlighted_line >= 0:
                        active_orig_idx = wrapped_to_orig.get(
                            current_highlighted_line, current_highlighted_line
                        )

            if current_highlighted_line >= 0 and not manual_scroll:
                target = max(0, current_highlighted_line - content_height // 2)
                target = min(target, max(0, len(lines) - content_height))
                scroll_pos = target

            # ── Header ──
            _safe_addstr(stdscr, 0, lm, "lyrics", accent)
            _safe_addstr(stdscr, 0, lm + 7, "//", sep_color)
            track_label = title
            if artist:
                track_label = f"{title} · {artist}"
            _safe_addstr(stdscr, 0, lm + 10, track_label[: cw - 12], future_color)

            _safe_addstr(stdscr, 1, lm, "─" * cw, border_color)

            # ── Lyrics content ──
            for i in range(content_height):
                line_idx = scroll_pos + i
                if line_idx >= len(lines):
                    break
                line = lines[line_idx]
                row = 2 + i
                is_symbol = line.strip() == "♪"
                display_text = "" if is_symbol else line

                # All wrapped sub-lines of the active lyric share the active state.
                line_orig_idx = wrapped_to_orig.get(line_idx, line_idx)
                is_active = active_orig_idx >= 0 and line_orig_idx == active_orig_idx
                is_past = active_orig_idx >= 0 and line_orig_idx < active_orig_idx

                if is_active:
                    _safe_addstr(stdscr, row, lm, "│", accent_n)
                    _safe_addstr(stdscr, row, lm + 2, "♪", accent_n)
                    _safe_addstr(stdscr, row, lm + 4, display_text[: cw - 6], active_color)
                elif is_past:
                    _safe_addstr(stdscr, row, lm, " ", past_color)
                    _safe_addstr(stdscr, row, lm + 4, display_text[: cw - 6], past_color)
                else:
                    _safe_addstr(stdscr, row, lm, " ", future_color)
                    _safe_addstr(stdscr, row, lm + 4, display_text[: cw - 6], future_color)

            # ── Footer ──
            footer_y = max_y - 2
            _safe_addstr(stdscr, footer_y, lm, "─" * cw, border_color)

            footer_y += 1
            _safe_addstr(stdscr, footer_y, lm, "J/K", accent_n)
            _safe_addstr(stdscr, footer_y, lm + 4, "scroll", sep_color)
            _safe_addstr(stdscr, footer_y, lm + 11, "│", sep_color)
            _safe_addstr(stdscr, footer_y, lm + 13, "Q", accent_n)
            _safe_addstr(stdscr, footer_y, lm + 15, "back", sep_color)

            total_lines = len(lines)
            if current_time > 0:
                time_str = f"{int(current_time // 60)}:{int(current_time % 60):02d}"
            else:
                time_str = "-:--"
            vis_start = max(1, scroll_pos + 1)
            vis_end = min(total_lines, scroll_pos + content_height)
            right_info = f"{time_str} │ [{vis_start}–{vis_end}/{total_lines}]"
            rx = lm + cw - len(right_info)
            _safe_addstr(stdscr, footer_y, rx, right_info, sep_color)

            stdscr.refresh()

            stdscr.timeout(200)
            key = stdscr.getch()

            if key == ord("q") or key == 27:
                break
            elif key == ord("j") or key == curses.KEY_DOWN:
                manual_scroll = True
                if scroll_pos + content_height < len(lines):
                    scroll_pos += 1
            elif key == ord("k") or key == curses.KEY_UP:
                manual_scroll = True
                if scroll_pos > 0:
                    scroll_pos -= 1
            elif key == curses.KEY_NPAGE:
                manual_scroll = True
                scroll_pos = min(scroll_pos + content_height, max(0, len(lines) - content_height))
            elif key == curses.KEY_PPAGE:
                manual_scroll = True
                scroll_pos = max(scroll_pos - content_height, 0)
            elif key == curses.KEY_HOME:
                manual_scroll = True
                scroll_pos = 0
            elif key == curses.KEY_END:
                manual_scroll = True
                scroll_pos = max(len(lines) - content_height, 0)
            elif key == ord(" "):
                manual_scroll = False

    return wrapper(lyrics_ui)


def selection_ui(stdscr, results, query, songs_to_display):
    """Interactive song selection UI using curses"""

    curses.curs_set(0)
    curses.use_default_colors()

    curses.init_pair(_CP_ACCENT, curses.COLOR_YELLOW, -1)
    curses.init_pair(_CP_DIM, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_TEXT, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)

    accent = curses.color_pair(_CP_ACCENT)
    accent_b = accent | curses.A_BOLD
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    border = curses.color_pair(_CP_BORDER) | curses.A_DIM
    green = curses.color_pair(3)

    current_selection = 0
    status_message = ""
    status_timer = 0

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        cw = min(max_x - 4, 70)
        lm = (max_x - cw) // 2

        row = 1
        _safe_addstr(stdscr, row, lm, "search", accent_b)
        _safe_addstr(stdscr, row, lm + 7, f"// {query}", dim)

        row += 1
        _safe_addstr(stdscr, row, lm, "─" * cw, border)

        row += 1
        shortcuts = [("↵", "play"), ("A", "add to playlist"), ("↑↓/JK", "navigate"), ("Q", "back")]
        col = lm
        for skey, slabel in shortcuts:
            _safe_addstr(stdscr, row, col, skey, accent)
            col += len(skey) + 1
            _safe_addstr(stdscr, row, col, slabel, dim)
            col += len(slabel) + 3

        row += 1
        _safe_addstr(stdscr, row, lm, "─" * cw, border)

        row += 1
        for i, song in enumerate(results[:songs_to_display]):
            if row + i >= max_y - 3:
                break

            title = song["title"]
            artist = song["artists"][0]["name"]
            line = f"{title} - {artist}"

            if len(line) > cw - 6:
                line = line[: cw - 9] + "..."

            r = row + i
            is_sel = i == current_selection

            try:
                if is_sel:
                    _safe_addstr(stdscr, r, lm, "›", accent_b)
                    _safe_addstr(stdscr, r, lm + 2, line, text | curses.A_BOLD)
                else:
                    num = str(i + 1)
                    _safe_addstr(stdscr, r, lm + 2 - len(num), num, dim)
                    _safe_addstr(stdscr, r, lm + 3, line, dim)
            except curses.error:
                safe_line = line.encode("ascii", "replace").decode("ascii")
                if is_sel:
                    _safe_addstr(stdscr, r, lm, f"› {safe_line}", accent_b)
                else:
                    _safe_addstr(stdscr, r, lm + 2, safe_line, dim)

        # Status message (temporary feedback)
        if status_message and time.time() - status_timer < 3:
            status_y = min(row + songs_to_display + 1, max_y - 3)
            _safe_addstr(stdscr, status_y, lm, status_message, green)
        elif time.time() - status_timer >= 3:
            status_message = ""

        # Footer
        footer_y = max_y - 2
        _safe_addstr(stdscr, footer_y, lm, "─" * cw, border)
        count_str = f"{min(songs_to_display, len(results))} RESULTS"
        _safe_addstr(stdscr, footer_y + 1, lm, count_str, border)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_DOWN, ord("j")):
            current_selection = (current_selection + 1) % songs_to_display
        elif key in (curses.KEY_UP, ord("k")):
            current_selection = (current_selection - 1 + songs_to_display) % songs_to_display
        elif key in (ord("\n"), 10, 13):
            return current_selection
        elif key == ord("q"):
            return None
        elif key == ord("a") or key == ord("A"):
            selected_song = results[current_selection]
            if add_song_to_playlist_ui(stdscr, selected_song):
                status_message = f"Added '{selected_song['title']}' to playlist!"
                status_timer = time.time()
        elif ord("1") <= key <= ord(str(min(9, songs_to_display))):
            return key - ord("1")


def add_song_to_playlist_ui(stdscr, song):
    """UI for adding a song to a playlist"""

    # Get available playlists
    playlists = playlist_manager.get_playlist_names()

    # If only one playlist exists, auto-select it (keep music simple!)
    if len(playlists) == 1:
        playlist_name = playlists[0]
        return playlist_manager.add_song_to_playlist(playlist_name, song)

    curses.curs_set(1)  # Show cursor for input
    _, max_x = stdscr.getmaxyx()

    # Clear and draw dialog
    stdscr.erase()

    # Title
    title = f"Add '{song['title']}' to playlist"
    if len(title) > max_x - 4:
        title = title[: max_x - 7] + "..."

    stdscr.addstr(2, 2, title)
    stdscr.addstr(3, 2, "─" * min(len(title), max_x - 4))

    current_line = 5

    if playlists:
        stdscr.addstr(current_line, 2, "Existing playlists:")
        current_line += 1

        for i, playlist_name in enumerate(playlists[:8]):  # Show max 8 playlists
            display_name = playlist_name
            if len(display_name) > max_x - 10:
                display_name = display_name[: max_x - 13] + "..."
            stdscr.addstr(current_line, 4, f"[{i + 1}] {display_name}")
            current_line += 1

        current_line += 1
        stdscr.addstr(current_line, 2, "Enter number to select existing playlist,")
        current_line += 1
        stdscr.addstr(current_line, 2, "or type new playlist name:")
    else:
        stdscr.addstr(current_line, 2, "No playlists found. Enter new playlist name:")
        current_line += 1

    current_line += 1
    stdscr.addstr(current_line, 2, "> ")
    stdscr.refresh()

    # Get user input
    curses.echo()
    input_str = ""
    try:
        input_bytes = stdscr.getstr(current_line, 4, max_x - 6)
        input_str = input_bytes.decode("utf-8").strip()
    except (curses.error, UnicodeDecodeError):
        input_str = ""
    finally:
        curses.noecho()
        curses.curs_set(0)

    if not input_str:
        return False

    # Check if it's a number (selecting existing playlist)
    if input_str.isdigit() and playlists:
        try:
            playlist_index = int(input_str) - 1
            if 0 <= playlist_index < len(playlists):
                playlist_name = playlists[playlist_index]
                return playlist_manager.add_song_to_playlist(playlist_name, song)
        except (ValueError, IndexError):
            pass

    # Treat as new playlist name
    playlist_name = input_str

    # Create playlist if it doesn't exist
    if playlist_name not in playlists:
        if not playlist_manager.create_playlist(playlist_name):
            return False

    # Add song to playlist
    return playlist_manager.add_song_to_playlist(playlist_name, song)


def _format_time(seconds):
    """Format seconds as m:ss"""
    if seconds is None or seconds < 0:
        return "-:--"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# Block characters for visualizer (index 0 = empty, 8 = full)
_VIS_BLOCKS = " ▁▂▃▄▅▆▇█"
_WAVE_ROWS = 3  # vertical rows per bar; total resolution = _WAVE_ROWS * 8 sub-units


def _draw_bar(scr, bottom_row, x, level, rows, attr):
    """Render a vertical bar at column x ending at bottom_row, `rows` tall."""
    total_units = rows * 8
    units = max(0, min(total_units, int(round(level * total_units))))
    for r_off in range(rows):
        cell = max(0, min(8, units - r_off * 8))
        ch = "█" if cell == 8 else _BLOCKS[cell]
        _safe_addstr(scr, bottom_row - r_off, x, ch, attr)


def _render_visualizer(bars, width):
    """Render cava bar values as a centered line of block characters."""
    if not bars:
        return ""
    vis = "".join(_VIS_BLOCKS[min(v, 8)] for v in bars)
    return vis.center(width)


def display_player_status(
    title,
    is_paused,
    track_index=None,
    track_total=None,
    elapsed=None,
    duration=None,
    visualizer_bars=None,
):
    """Display player status (non-curses fallback for non-TTY)"""
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80

    sys.stdout.write("\033[H\033[2J")

    status = "\u23f8\ufe0f  Paused" if is_paused else "\u25b6\ufe0f  Playing"
    if track_index is not None and track_total is not None:
        status += f" [{track_index}/{track_total}]"

    lines = ["", status.center(width), "", title.center(width)[:width], ""]

    if visualizer_bars:
        lines.append(_render_visualizer(visualizer_bars, width))
    else:
        lines.append("")

    if elapsed is not None and duration and duration > 0:
        time_str = f" {_format_time(elapsed)} / {_format_time(duration)} "
        bar_width = min(width - 2, 40)
        filled = int(bar_width * min(elapsed / duration, 1.0))
        empty = bar_width - filled
        bar = "\u2593" * filled + "\u2591" * empty
        bar_line = f"{bar}{time_str}"
        lines.append(bar_line.center(width))
    else:
        lines.append("")

    controls = "\u23ee\ufe0f b  \u23ef\ufe0f space  \u23ed\ufe0f n  \U0001f4dc l  \u2764\ufe0f a  \U0001f44e d  \U0001f6aa q"
    lines.append("")
    lines.append(controls.center(width))

    sys.stdout.write("\n".join(lines))
    sys.stdout.flush()


# \u2500\u2500 Curses player UI (redesigned) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

_WAVE_BARS = 24
_WAVE_SEEDS = [
    6,
    18,
    10,
    30,
    14,
    38,
    8,
    28,
    22,
    12,
    36,
    16,
    24,
    8,
    32,
    18,
    6,
    28,
    14,
    20,
    34,
    10,
    26,
    16,
]
_BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

# Rolling history of real audio samples driving the visualizer.
# Each entry is (left, right) in 0..1 \u2014 newest on the right.
_WAVE_HISTORY: deque[tuple[float, float]] = deque(maxlen=_WAVE_BARS * 2)
_WAVE_PREV_PEAK = 0.0


def reset_wave_history():
    """Clear visualizer history (call on track change)."""
    global _WAVE_PREV_PEAK
    _WAVE_HISTORY.clear()
    _WAVE_PREV_PEAK = 0.0


def push_wave_sample(levels):
    """Append a real audio sample from get_mpv_audio_levels output."""
    global _WAVE_PREV_PEAK
    if not levels:
        return
    peak = levels.get("peak")
    if peak is None:
        peak = levels.get("rms") or 0.0
    # Light smoothing keeps bars from flickering between adjacent ticks.
    smoothed = max(peak, _WAVE_PREV_PEAK * 0.6)
    _WAVE_PREV_PEAK = smoothed
    left = levels.get("left")
    right = levels.get("right")
    if left is None:
        left = smoothed
    if right is None:
        right = smoothed
    # Bias each channel by current peak so silent stretches still drop to 0.
    _WAVE_HISTORY.append((min(1.0, left), min(1.0, right)))


_CP_ACCENT = 10
_CP_DIM = 11
_CP_TEXT = 12
_CP_BORDER = 13


def init_player_colors():
    """Initialize color pairs for the player UI."""
    curses.use_default_colors()
    curses.init_pair(_CP_ACCENT, curses.COLOR_YELLOW, -1)
    curses.init_pair(_CP_DIM, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_TEXT, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_BORDER, curses.COLOR_WHITE, -1)


def _safe_addstr(scr, y, x, text, attr=0):
    """Write text clipped to screen bounds."""
    h, w = scr.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    text = text[: max(0, w - x - 1)]
    if text:
        try:
            scr.addstr(y, max(0, x), text, attr)
        except curses.error:
            pass


def draw_player(
    scr,
    song_title,
    artist,
    is_paused,
    track_idx,
    track_total,
    elapsed,
    duration,
    frame=0,
    toast_msg=None,
    toast_expire=0,
    audio_levels=None,
    bands=None,
):
    """Render full-screen player UI."""
    scr.erase()
    h, w = scr.getmaxyx()
    cx = w // 2

    accent = curses.color_pair(_CP_ACCENT) | curses.A_BOLD
    accent_n = curses.color_pair(_CP_ACCENT)
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    bdr = curses.color_pair(_CP_BORDER) | curses.A_DIM

    cw = min(w - 4, 70)
    lm = (w - cw) // 2

    r = max(1, (h - 18) // 2)

    # \u2500\u2500 Header \u2500\u2500
    _safe_addstr(scr, r, lm, "ytm", accent)
    _safe_addstr(scr, r, lm + 4, "// youtube music cli", dim)

    state = "playing" if not is_paused else "paused"
    status = f"\u25cf {state} [{track_idx}/{track_total}]"
    sx = lm + cw - len(status)
    _safe_addstr(scr, r, sx, "\u25cf", accent_n if not is_paused else dim)
    _safe_addstr(scr, r, sx + 2, f"{state} [{track_idx}/{track_total}]", dim)

    r += 1
    _safe_addstr(scr, r, lm, "\u2500" * cw, bdr)

    # \u2500\u2500 Waveform / Spectrum \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # Priority: real FFT spectrum (ffmpeg+numpy) > stereo oscilloscope (astats)
    # > synthesized fallback (no audio backend reporting yet).
    r += 1
    nbars = min(_WAVE_BARS, (cw - 4 + 1) // 2)
    ww = nbars * 2 - 1
    wx = cx - ww // 2
    half = nbars // 2

    bar_bottom = r + _WAVE_ROWS - 1
    bar_attr = accent_n if not is_paused else dim

    history = list(_WAVE_HISTORY)
    have_real = bool(history) and audio_levels is not None

    if bands:
        mode_label = "spectrum"
        n_in = len(bands)
        for i in range(nbars):
            lo = int(i * n_in / nbars)
            hi = max(lo + 1, int((i + 1) * n_in / nbars))
            level = max(bands[lo:hi])
            if is_paused:
                level *= 0.3
            _draw_bar(scr, bar_bottom, wx + i * 2, level, _WAVE_ROWS, bar_attr)
    elif have_real:
        mode_label = ""
        recent = history[-half:] if half else []
        recent = [(0.0, 0.0)] * max(0, half - len(recent)) + recent

        for i in range(nbars):
            if i < half:
                level = recent[i][0]
            elif nbars % 2 == 1 and i == half:
                lch, rch = recent[-1] if recent else (0.0, 0.0)
                level = (lch + rch) / 2.0
            else:
                level = recent[nbars - 1 - i][1]

            if is_paused:
                level *= 0.3
            _draw_bar(scr, bar_bottom, wx + i * 2, level, _WAVE_ROWS, bar_attr)
    else:
        mode_label = "sim"
        for i in range(nbars):
            if not is_paused:
                seed = _WAVE_SEEDS[i % len(_WAVE_SEEDS)]
                phase = frame * 0.7 + i * 0.65
                val = 0.5 + 0.5 * math.sin(phase)
                level = (seed / 40.0) * (0.4 + 0.6 * val)
            else:
                level = 0.05
            _draw_bar(scr, bar_bottom, wx + i * 2, level, _WAVE_ROWS, bar_attr)

    # Mode indicator: lets you confirm which visualizer pipeline is live.
    label_row = bar_bottom + 1
    label_x = lm + cw - len(mode_label)
    _safe_addstr(scr, label_row, label_x, mode_label, dim)

    r = label_row

    # \u2500\u2500 Song info \u2500\u2500
    r += 2
    dt = song_title[:cw]
    _safe_addstr(scr, r, max(0, cx - len(dt) // 2), dt, text | curses.A_BOLD)
    r += 1
    da = artist[:cw]
    _safe_addstr(scr, r, max(0, cx - len(da) // 2), da, dim)

    # \u2500\u2500 Progress \u2500\u2500
    r += 2
    bw = min(cw - 8, 48)
    bx = cx - bw // 2
    if elapsed is not None and duration and duration > 0:
        pct = min(elapsed / duration, 1.0)
        filled = int(bw * pct)
        _safe_addstr(scr, r, bx, "\u2501" * filled, accent_n)
        _safe_addstr(scr, r, bx + filled, "\u2501" * (bw - filled), dim)
        r += 1
        el_s = _format_time(elapsed)
        du_s = _format_time(duration)
        _safe_addstr(scr, r, bx, el_s, dim)
        _safe_addstr(scr, r, bx + bw - len(du_s), du_s, dim)
    else:
        _safe_addstr(scr, r, bx, "\u2501" * bw, dim)
        r += 1

    # \u2500\u2500 Controls \u2500\u2500
    r += 2
    _safe_addstr(scr, r, lm, "\u2500" * cw, bdr)
    r += 1
    pl = "play" if is_paused else "pause"
    ctrl = f"[B] prev  [SPC] {pl}  [N] next  \u2502  [A] playlist  [D] dislike  \u2502  [L] lyrics  [Q] quit"
    if len(ctrl) > cw:
        ctrl = f"[B]prev [SPC]{pl} [N]next \u2502 [A]add [D]dis \u2502 [L]lyr [Q]quit"
    _draw_ctrl_line(scr, r, max(0, cx - len(ctrl) // 2), ctrl, accent_n, dim)

    # \u2500\u2500 Hint \u2500\u2500
    r += 2
    hint = (
        "KEYBOARD SHORTCUTS ACTIVE \u2014 B \u00b7 SPC \u00b7 N \u00b7 A \u00b7 D \u00b7 L \u00b7 Q"
    )
    if len(hint) <= cw:
        _safe_addstr(scr, r, max(0, cx - len(hint) // 2), hint, bdr)

    # \u2500\u2500 Toast \u2500\u2500
    if toast_msg and time.time() < toast_expire:
        ty = min(h - 2, r + 2)
        _safe_addstr(
            scr, ty, max(0, cx - len(toast_msg) // 2 - 1), f" {toast_msg} ", text | curses.A_REVERSE
        )

    scr.refresh()


def _draw_ctrl_line(scr, row, x, line, key_attr, text_attr):
    """Draw control line with [KEY] portions highlighted."""
    _safe_addstr(scr, row, x, line, text_attr)
    col = x
    i = 0
    while i < len(line):
        if line[i] == "[":
            j = line.index("]", i) + 1
            _safe_addstr(scr, row, col, line[i:j], key_attr)
            col += j - i
            i = j
        else:
            col += 1
            i += 1
