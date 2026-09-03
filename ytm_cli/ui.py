"""User interface components for YTM CLI"""

import curses
import math
import os
import sys
import time
from collections import deque
from curses import wrapper

from .playlists import playlist_manager
from .utils import ADD_ICON, PAUSE_ICON, PLAY_ICON, player_controls

_UI_MAX_WIDTH = 76
_CP_ACCENT = 10
_CP_DIM = 11
_CP_TEXT = 12
_CP_BORDER = 13
_CP_SUCCESS = 14


def init_ui_colors():
    """Initialize the shared terminal color palette."""
    curses.use_default_colors()
    curses.init_pair(_CP_ACCENT, curses.COLOR_YELLOW, -1)
    curses.init_pair(_CP_DIM, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_TEXT, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_BORDER, curses.COLOR_WHITE, -1)
    curses.init_pair(_CP_SUCCESS, curses.COLOR_GREEN, -1)


def _screen_bounds(scr, max_width=_UI_MAX_WIDTH):
    """Return responsive screen and centered-content dimensions."""
    height, width = scr.getmaxyx()
    content_width = max(1, min(max(1, width - 4), max_width))
    left_margin = max(0, (width - content_width) // 2)
    return height, width, content_width, left_margin


def _draw_screen_header(scr, row, left, width, section, right, accent, dim, border):
    """Draw the shared YTM section header and divider."""
    _safe_addstr(scr, row, left, "YTM", accent)
    _safe_addstr(scr, row, left + 4, f"// {section.upper()}", dim)
    if right:
        right = _ellipsize(right, width)
        right_x = left + width - len(right)
        minimum_x = left + len(section) + 8
        if right_x > minimum_x:
            _safe_addstr(scr, row, right_x, right, dim)
    _safe_addstr(scr, row + 1, left, "─" * width, border)
    return row + 2


def _draw_screen_footer(scr, row, left, width, hints, right, accent, dim, border):
    """Draw the shared divider, key hints, and optional right-side status."""
    _safe_addstr(scr, row, left, "─" * width, border)
    hints = _ellipsize(hints, width)
    _draw_ctrl_line(scr, row + 1, left, hints, accent, dim)
    if right and len(hints) + len(right) + 2 <= width:
        _safe_addstr(scr, row + 1, left + width - len(right), right, dim)


def display_lyrics_with_curses(
    lyrics_data,
    title,
    artist=None,
    socket_path=None,
    get_mpv_time_position_func=None,
    is_playing_func=None,
):
    """Display lyrics using curses with live highlighting"""

    def lyrics_ui(stdscr):
        curses.curs_set(0)
        init_ui_colors()

        accent = curses.color_pair(_CP_ACCENT) | curses.A_BOLD
        accent_n = curses.color_pair(_CP_ACCENT)
        future_color = curses.color_pair(_CP_DIM) | curses.A_DIM
        past_color = curses.color_pair(_CP_DIM) | curses.A_DIM
        active_color = curses.color_pair(_CP_TEXT) | curses.A_BOLD
        sep_color = curses.color_pair(_CP_DIM) | curses.A_DIM
        border_color = curses.color_pair(_CP_BORDER) | curses.A_DIM

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

        max_y, _, cw, lm = _screen_bounds(stdscr)
        line_width = max(1, cw - 6)

        wrapped_lines = []
        timestamp_map = {}
        # Map each wrapped line index → original lyric index, so all sub-lines
        # of a wrapped lyric share the same active/past/future state.
        wrapped_to_orig = {}

        for orig_idx, line in enumerate(lines):
            if len(line) <= line_width:
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
                    if len(current_line + " " + word) <= line_width:
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
        content_start = 4
        footer_row = max_y - 2
        content_height = max(0, footer_row - content_start)
        inactive_polls = 0

        while True:
            if is_playing_func:
                if is_playing_func():
                    inactive_polls = 0
                else:
                    inactive_polls += 1
                    if inactive_polls >= 2:
                        break

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
            mode = "MANUAL" if manual_scroll else "SYNCED" if timestamped_lyrics else "STATIC"
            _draw_screen_header(
                stdscr,
                0,
                lm,
                cw,
                "lyrics",
                mode,
                accent,
                sep_color,
                border_color,
            )
            track_label = title
            if artist:
                track_label = f"{title} · {artist}"
            _safe_addstr(stdscr, 2, lm, "NOW SINGING", accent_n)
            _safe_addstr(stdscr, 2, lm + 13, _ellipsize(track_label, max(1, cw - 13)), future_color)

            # ── Lyrics content ──
            for i in range(content_height):
                line_idx = scroll_pos + i
                if line_idx >= len(lines):
                    break
                line = lines[line_idx]
                row = content_start + i
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
            total_lines = len(lines)
            if current_time > 0:
                time_str = f"{int(current_time // 60)}:{int(current_time % 60):02d}"
            else:
                time_str = "-:--"
            vis_start = max(1, scroll_pos + 1)
            vis_end = min(total_lines, scroll_pos + content_height)
            right_info = f"{time_str} · {vis_start}–{vis_end}/{total_lines}"
            _draw_screen_footer(
                stdscr,
                footer_row,
                lm,
                cw,
                "[J/K] scroll  [SPACE] sync  [Q] back",
                right_info,
                accent_n,
                sep_color,
                border_color,
            )

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
    init_ui_colors()

    accent = curses.color_pair(_CP_ACCENT)
    accent_b = accent | curses.A_BOLD
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    border = curses.color_pair(_CP_BORDER) | curses.A_DIM
    green = curses.color_pair(_CP_SUCCESS) | curses.A_BOLD

    current_selection = 0
    status_message = ""
    status_timer = 0
    display_count = min(songs_to_display, len(results))
    if display_count == 0:
        return None

    while True:
        stdscr.erase()
        max_y, _, cw, lm = _screen_bounds(stdscr)
        footer_row = max_y - 2

        row = _draw_screen_header(
            stdscr,
            0,
            lm,
            cw,
            "search",
            f"{display_count} RESULTS",
            accent_b,
            dim,
            border,
        )
        _safe_addstr(stdscr, row, lm, "RESULTS FOR", accent)
        _safe_addstr(stdscr, row, lm + 13, _ellipsize(query, max(1, cw - 13)), dim)

        list_start = row + 2
        list_height = max(1, footer_row - list_start - 1)
        window_start = max(0, current_selection - list_height + 1)
        window_end = min(display_count, window_start + list_height)

        for visible_row, i in enumerate(range(window_start, window_end)):
            song = results[i]

            title = song["title"]
            artists = song.get("artists") or []
            artist = artists[0].get("name", "Unknown Artist") if artists else "Unknown Artist"
            line = _ellipsize(f"{title} · {artist}", max(1, cw - 7))

            r = list_start + visible_row
            is_sel = i == current_selection
            number = f"{i + 1:02d}"

            try:
                if is_sel:
                    _safe_addstr(stdscr, r, lm, "›", accent_b)
                    _safe_addstr(stdscr, r, lm + 2, number, accent_b)
                    _safe_addstr(stdscr, r, lm + 6, line, text | curses.A_BOLD)
                else:
                    _safe_addstr(stdscr, r, lm + 2, number, dim)
                    _safe_addstr(stdscr, r, lm + 6, line, dim)
            except curses.error:
                safe_line = line.encode("ascii", "replace").decode("ascii")
                if is_sel:
                    _safe_addstr(stdscr, r, lm, f"› {number}  {safe_line}", accent_b)
                else:
                    _safe_addstr(stdscr, r, lm + 2, f"{number}  {safe_line}", dim)

        # Status message (temporary feedback)
        if status_message and time.time() - status_timer < 3:
            _safe_addstr(stdscr, footer_row - 1, lm, _ellipsize(f"✓ {status_message}", cw), green)
        elif time.time() - status_timer >= 3:
            status_message = ""

        # Footer
        _draw_screen_footer(
            stdscr,
            footer_row,
            lm,
            cw,
            "[ENTER] play  [A] save  [↑↓/JK] move  [Q] back",
            f"{current_selection + 1}/{display_count}",
            accent,
            dim,
            border,
        )

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_DOWN, ord("j")):
            current_selection = (current_selection + 1) % display_count
        elif key in (curses.KEY_UP, ord("k")):
            current_selection = (current_selection - 1) % display_count
        elif key in (ord("\n"), 10, 13):
            return current_selection
        elif key == ord("q"):
            return None
        elif key == ord("a") or key == ord("A"):
            selected_song = results[current_selection]
            if add_song_to_playlist_ui(stdscr, selected_song):
                status_message = f"Added '{selected_song['title']}' to playlist!"
                status_timer = time.time()
        elif ord("1") <= key <= ord(str(min(9, display_count))):
            return key - ord("1")


def select_playlist_ui(stdscr, song_title, playlists):
    """Select an existing playlist or request creation of a new one."""
    if len(playlists) == 1:
        return playlists[0]

    curses.curs_set(0)
    init_ui_colors()

    accent = curses.color_pair(_CP_ACCENT)
    accent_b = accent | curses.A_BOLD
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    border = curses.color_pair(_CP_BORDER) | curses.A_DIM

    options = [(f"{ADD_ICON}  Create new playlist", "CREATE_NEW")]
    options.extend((name, name) for name in playlists)
    selected_index = 0

    while True:
        stdscr.erase()
        height, _, width, left = _screen_bounds(stdscr)
        footer_row = height - 2
        row = _draw_screen_header(
            stdscr,
            0,
            left,
            width,
            "save track",
            f"{len(playlists)} PLAYLISTS",
            accent_b,
            dim,
            border,
        )
        _safe_addstr(stdscr, row, left, "TRACK", accent)
        _safe_addstr(stdscr, row, left + 7, _ellipsize(song_title, max(1, width - 7)), dim)

        list_start = row + 2
        list_height = max(1, footer_row - list_start)
        window_start = max(0, selected_index - list_height + 1)
        window_end = min(len(options), window_start + list_height)
        for visible_row, i in enumerate(range(window_start, window_end)):
            label, _ = options[i]
            item_row = list_start + visible_row
            label = _ellipsize(label, max(1, width - 6))
            if i == selected_index:
                _safe_addstr(stdscr, item_row, left, "›", accent_b)
                _safe_addstr(stdscr, item_row, left + 2, label, text | curses.A_BOLD)
            else:
                _safe_addstr(stdscr, item_row, left + 2, label, dim)

        _draw_screen_footer(
            stdscr,
            footer_row,
            left,
            width,
            "[ENTER] choose  [↑↓/JK] move  [Q] cancel",
            f"{selected_index + 1}/{len(options)}",
            accent,
            dim,
            border,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            return None
        if key in (ord("j"), curses.KEY_DOWN):
            selected_index = (selected_index + 1) % len(options)
        elif key in (ord("k"), curses.KEY_UP):
            selected_index = (selected_index - 1) % len(options)
        elif key in (10, 13, curses.KEY_ENTER):
            return options[selected_index][1]


def new_playlist_name_ui(stdscr, song_title):
    """Prompt for a new playlist name using the shared save-track screen."""
    curses.curs_set(1)
    init_ui_colors()
    stdscr.erase()

    max_y, max_x, width, left = _screen_bounds(stdscr)
    accent = curses.color_pair(_CP_ACCENT)
    accent_b = accent | curses.A_BOLD
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    border = curses.color_pair(_CP_BORDER) | curses.A_DIM

    row = _draw_screen_header(
        stdscr,
        0,
        left,
        width,
        "save track",
        "NEW PLAYLIST",
        accent_b,
        dim,
        border,
    )
    _safe_addstr(stdscr, row, left, "TRACK", accent)
    _safe_addstr(
        stdscr,
        row,
        left + 7,
        _ellipsize(song_title, max(1, width - 7)),
        text | curses.A_BOLD,
    )
    _safe_addstr(
        stdscr,
        row + 2,
        left,
        _ellipsize("Leave blank to generate a playlist name automatically.", width),
        dim,
    )

    input_row = max(0, max_y - 1)
    _safe_addstr(stdscr, max(0, input_row - 1), left, "─" * width, border)
    prompt = "PLAYLIST › "
    _safe_addstr(stdscr, input_row, left, prompt, accent_b)
    stdscr.refresh()

    curses.echo()
    try:
        input_x = min(max_x - 1, left + len(prompt))
        value = stdscr.getstr(input_row, input_x, max(1, max_x - input_x - 1))
        return value.decode("utf-8").strip()
    except (curses.error, UnicodeDecodeError):
        return ""
    finally:
        curses.noecho()
        curses.curs_set(0)


def add_song_to_playlist_ui(stdscr, song):
    """Add a song to an existing or newly named playlist."""

    # Get available playlists
    playlists = playlist_manager.get_playlist_names()

    # If only one playlist exists, auto-select it (keep music simple!)
    if len(playlists) == 1:
        playlist_name = playlists[0]
        return playlist_manager.add_song_to_playlist(playlist_name, song, notify=False)

    curses.curs_set(1)
    init_ui_colors()
    stdscr.erase()
    max_y, max_x, width, left = _screen_bounds(stdscr)
    accent = curses.color_pair(_CP_ACCENT)
    accent_b = accent | curses.A_BOLD
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    border = curses.color_pair(_CP_BORDER) | curses.A_DIM

    row = _draw_screen_header(
        stdscr,
        0,
        left,
        width,
        "save track",
        f"{len(playlists)} PLAYLISTS",
        accent_b,
        dim,
        border,
    )
    _safe_addstr(stdscr, row, left, "TRACK", accent)
    _safe_addstr(
        stdscr,
        row,
        left + 7,
        _ellipsize(song.get("title", "Unknown"), max(1, width - 7)),
        text | curses.A_BOLD,
    )

    row += 2

    if playlists:
        _safe_addstr(stdscr, row, left, "DESTINATIONS", accent)
        row += 1
        max_options = max(0, min(8, max_y - row - 4))
        for i, playlist_name in enumerate(playlists[:max_options]):
            _safe_addstr(stdscr, row, left + 2, f"[{i + 1}]", accent)
            _safe_addstr(
                stdscr,
                row,
                left + 6,
                _ellipsize(playlist_name, max(1, width - 6)),
                dim,
            )
            row += 1
        instruction = "Enter a number to reuse a playlist, or type a new name."
    else:
        instruction = "No playlists yet. Type a name to create the first one."

    input_row = max(0, max_y - 1)
    _safe_addstr(stdscr, max(0, input_row - 2), left, _ellipsize(instruction, width), dim)
    _safe_addstr(stdscr, max(0, input_row - 1), left, "─" * width, border)
    prompt = "PLAYLIST › "
    _safe_addstr(stdscr, input_row, left, prompt, accent_b)
    stdscr.refresh()

    # Get user input
    curses.echo()
    input_str = ""
    try:
        input_x = min(max_x - 1, left + len(prompt))
        input_bytes = stdscr.getstr(input_row, input_x, max(1, max_x - input_x - 1))
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
                return playlist_manager.add_song_to_playlist(playlist_name, song, notify=False)
        except (ValueError, IndexError):
            pass

    # Treat as new playlist name
    playlist_name = input_str

    # Create playlist if it doesn't exist
    if playlist_name not in playlists:
        if not playlist_manager.create_playlist(playlist_name, notify=False):
            return False

    # Add song to playlist
    return playlist_manager.add_song_to_playlist(playlist_name, song, notify=False)


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
        terminal_width = max(1, os.get_terminal_size().columns)
    except OSError:
        terminal_width = 80

    sys.stdout.write("\033[H\033[2J")

    content_width = max(1, min(max(1, terminal_width - 4), _UI_MAX_WIDTH))
    left = max(0, (terminal_width - content_width) // 2)
    prefix = " " * left

    state = f"{PAUSE_ICON} PAUSED" if is_paused else f"{PLAY_ICON} PLAYING"
    if track_index is not None and track_total is not None:
        state += f"  {track_index} / {track_total}"

    brand = "YTM // PLAYER"
    if len(brand) + len(state) + 2 <= content_width:
        header = f"{brand}{' ' * (content_width - len(brand) - len(state))}{state}"
    else:
        header = _ellipsize(state, content_width)

    def content_line(value, centered=False):
        value = _ellipsize(value, content_width)
        if centered:
            value = value.center(content_width)
        return f"{prefix}{value}"[:terminal_width]

    lines = [
        content_line(header),
        content_line("─" * content_width),
        "",
        content_line("NOW PLAYING", centered=True),
        content_line(title, centered=True),
        "",
    ]

    if visualizer_bars:
        lines.append(content_line(_render_visualizer(visualizer_bars, content_width)))
    else:
        lines.append("")

    if elapsed is not None and duration and duration > 0:
        time_str = f" {_format_time(elapsed)} / {_format_time(duration)} "
        bar_width = max(0, min(content_width - len(time_str), 40))
        filled = int(bar_width * min(elapsed / duration, 1.0))
        empty = bar_width - filled
        bar = "\u2593" * filled + "\u2591" * empty
        bar_line = f"{bar}{time_str}"
        lines.append(content_line(bar_line, centered=True))
    else:
        lines.append("")

    controls = player_controls(is_paused)
    playback_controls = "  ".join(f"{icon} {key}" for icon, key, _ in controls[:3])
    library_controls = "  ".join(f"{icon} {key}" for icon, key, _ in controls[3:])
    lines.append("")
    lines.append(content_line(playback_controls, centered=True))
    lines.append(content_line(library_controls, centered=True))

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


def init_player_colors():
    """Initialize color pairs for the player UI."""
    init_ui_colors()


def _safe_addstr(scr, y, x, text, attr=0):
    """Write text clipped to screen bounds."""
    h, w = scr.getmaxyx()
    if y < 0 or y >= h or w <= 1:
        return
    x = max(0, x)
    if x >= w:
        return
    text = text[: max(0, w - x - 1)]
    if text:
        try:
            scr.addstr(y, x, text, attr)
        except curses.error:
            pass


def _ellipsize(text, width):
    """Fit text to a terminal width while preserving a visible truncation cue."""
    text = str(text or "")
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return f"{text[: width - 1]}…"


def _draw_progress_bar(scr, row, x, width, elapsed, duration, active_attr, empty_attr):
    """Repaint the complete bar before drawing its single playhead."""
    _safe_addstr(scr, row, x, "─" * width, empty_attr)
    if elapsed is None or not duration or duration <= 0:
        return

    pct = max(0.0, min(elapsed / duration, 1.0))
    playhead = int((width - 1) * pct)
    _safe_addstr(scr, row, x, "━" * playhead + "●", active_attr)


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
    next_title=None,
    next_artist=None,
    toast_detail=None,
):
    """Render the responsive full-screen player UI."""
    scr.clear()
    h, w = scr.getmaxyx()
    cx = w // 2

    accent = curses.color_pair(_CP_ACCENT) | curses.A_BOLD
    accent_n = curses.color_pair(_CP_ACCENT)
    dim = curses.color_pair(_CP_DIM) | curses.A_DIM
    text = curses.color_pair(_CP_TEXT)
    bdr = curses.color_pair(_CP_BORDER) | curses.A_DIM

    cw = max(1, min(w - 4, 76))
    lm = (w - cw) // 2
    state = "PAUSED" if is_paused else "PLAYING"
    state_icon = PAUSE_ICON if is_paused else PLAY_ICON
    position = f"{track_idx} / {track_total}"
    toast_visible = bool(toast_msg and time.time() < toast_expire)
    compact = h < 18 or cw < 58
    control_items = player_controls(is_paused)

    # The compact layout keeps the core controls usable in short or narrow terminals.
    if compact:
        header = f"{state_icon} {state}  {position}"
        if len(header) + 5 <= cw:
            _safe_addstr(scr, 0, lm, "YTM", accent)
        header_x = lm + cw - len(header)
        _safe_addstr(scr, 0, header_x, state_icon, accent_n)
        _safe_addstr(scr, 0, header_x + len(state_icon) + 1, header[len(state_icon) + 1 :], dim)
        if h > 2:
            _safe_addstr(scr, 1, lm, "─" * cw, bdr)

        footer_row = h - 1
        two_line_controls = h >= 8
        separator_row = footer_row - (2 if two_line_controls else 1)
        content_end = max(2, separator_row)
        content_lines = 3 + int(elapsed is not None and duration and duration > 0)
        if toast_visible:
            content_lines += 2 if toast_detail else 1
        else:
            content_lines += int(bool(next_title))
        available_lines = max(0, content_end - 2)
        row = 2 + max(0, (available_lines - content_lines) // 2) if h > 3 else 1

        title = _ellipsize(song_title, cw)
        _safe_addstr(scr, row, max(lm, cx - len(title) // 2), title, text | curses.A_BOLD)
        row += 1

        if row < content_end:
            artist_line = _ellipsize(artist, cw)
            _safe_addstr(scr, row, max(lm, cx - len(artist_line) // 2), artist_line, dim)
            row += 1

        progress_width = max(1, min(cw, 48))
        progress_x = cx - progress_width // 2
        if row < content_end:
            _draw_progress_bar(
                scr,
                row,
                progress_x,
                progress_width,
                elapsed,
                duration,
                accent_n,
                dim,
            )
            row += 1

        if row < content_end and elapsed is not None and duration and duration > 0:
            time_line = f"{_format_time(elapsed)}  /  {_format_time(duration)}"
            _safe_addstr(scr, row, max(lm, cx - len(time_line) // 2), time_line, dim)
            row += 1

        if row < content_end:
            if toast_visible:
                if toast_detail and row + 1 < content_end:
                    headline = _ellipsize(toast_msg, cw)
                    detail = _ellipsize(toast_detail, cw)
                    _safe_addstr(scr, row, max(lm, cx - len(headline) // 2), headline, accent)
                    _safe_addstr(scr, row + 1, max(lm, cx - len(detail) // 2), detail, dim)
                else:
                    message = f" {_ellipsize(toast_msg, max(1, cw - 2))} "
                    _safe_addstr(
                        scr,
                        row,
                        max(lm, cx - len(message) // 2),
                        message,
                        text | curses.A_REVERSE,
                    )
            elif next_title:
                queue_text = next_title
                if next_artist:
                    queue_text = f"{queue_text} · {next_artist}"
                queue_line = _ellipsize(f"NEXT  {queue_text}", cw)
                _safe_addstr(scr, row, lm, queue_line[:4], accent_n)
                _safe_addstr(scr, row, lm + 4, queue_line[4:], dim)

        if h > 4:
            _safe_addstr(scr, separator_row, lm, "─" * cw, bdr)
        if two_line_controls:
            playback_controls = "  ".join(
                f"{icon}[{'SPC' if key == 'space' else key.upper()}]"
                for icon, key, _ in control_items[:3]
            )
            library_controls = "  ".join(
                f"{icon}[{key.upper()}]" for icon, key, _ in control_items[3:]
            )
            if len(playback_controls) > cw:
                playback_controls = "[B] [SPC] [N]"
            if len(library_controls) > cw:
                library_controls = "[L] [A] [D] [Q]"
            _draw_ctrl_line(
                scr,
                footer_row - 1,
                max(lm, cx - len(playback_controls) // 2),
                playback_controls,
                accent_n,
                dim,
            )
            _draw_ctrl_line(
                scr,
                footer_row,
                max(lm, cx - len(library_controls) // 2),
                library_controls,
                accent_n,
                dim,
            )
        else:
            key_controls = "[B] [SPC] [N] · [L] [A] [D] [Q]"
            controls = key_controls if len(key_controls) <= cw else "B S N · L A D Q"
            controls = _ellipsize(controls, cw)
            _draw_ctrl_line(
                scr,
                footer_row,
                max(lm, cx - len(controls) // 2),
                controls,
                accent_n,
                dim,
            )
        scr.refresh()
        return

    top = max(0, (h - 18) // 2)

    # Header: brand, playback state, and queue position form one scan line.
    _safe_addstr(scr, top, lm, "YTM", accent)
    _safe_addstr(scr, top, lm + 4, "// PLAYER", dim)
    header = f"{state_icon} {state}  {position}"
    header_x = lm + cw - len(header)
    _safe_addstr(scr, top, header_x, state_icon, accent_n)
    _safe_addstr(scr, top, header_x + len(state_icon) + 1, header[len(state_icon) + 1 :], dim)
    _safe_addstr(scr, top + 1, lm, "─" * cw, bdr)

    # Visualizer priority: FFT spectrum, stereo audio history, then animated fallback.
    nbars = min(_WAVE_BARS, (cw + 1) // 2)
    wave_width = nbars * 2 - 1
    wave_x = cx - wave_width // 2
    half = nbars // 2
    bar_bottom = top + 5
    bar_attr = accent_n if not is_paused else dim
    history = list(_WAVE_HISTORY)
    have_real = bool(history) and audio_levels is not None

    if is_paused:
        now = time.time()
        for i in range(nbars):
            distance = abs(i - nbars / 2.0) / (nbars / 2.0)
            phase = now * 1.2 - distance * 2.5
            level = 0.08 + 0.12 * (0.5 + 0.5 * math.sin(phase))
            _draw_bar(scr, bar_bottom, wave_x + i * 2, level, _WAVE_ROWS, bar_attr)
    elif bands:
        band_count = len(bands)
        for i in range(nbars):
            low = int(i * band_count / nbars)
            high = max(low + 1, int((i + 1) * band_count / nbars))
            _draw_bar(scr, bar_bottom, wave_x + i * 2, max(bands[low:high]), _WAVE_ROWS, bar_attr)
    elif have_real:
        recent = history[-half:] if half else []
        recent = [(0.0, 0.0)] * max(0, half - len(recent)) + recent
        for i in range(nbars):
            if i < half:
                level = recent[i][0]
            elif nbars % 2 == 1 and i == half:
                left, right = recent[-1] if recent else (0.0, 0.0)
                level = (left + right) / 2.0
            else:
                level = recent[nbars - 1 - i][1]
            _draw_bar(scr, bar_bottom, wave_x + i * 2, level, _WAVE_ROWS, bar_attr)
    else:
        for i in range(nbars):
            seed = _WAVE_SEEDS[i % len(_WAVE_SEEDS)]
            phase = frame * 0.7 + i * 0.65
            level = (seed / 40.0) * (0.7 + 0.3 * math.sin(phase))
            _draw_bar(scr, bar_bottom, wave_x + i * 2, level, _WAVE_ROWS, bar_attr)

    # Track identity is deliberately the strongest element on screen.
    overline = "NOW PLAYING"
    _safe_addstr(scr, top + 7, cx - len(overline) // 2, overline, accent_n)
    title = _ellipsize(song_title, cw)
    _safe_addstr(scr, top + 8, cx - len(title) // 2, title, text | curses.A_BOLD)
    artist_line = _ellipsize(artist, cw)
    _safe_addstr(scr, top + 9, cx - len(artist_line) // 2, artist_line, dim)

    # Progress uses a distinct playhead instead of an ambiguous two-color line.
    progress_width = min(cw - 10, 56)
    progress_x = cx - progress_width // 2
    _draw_progress_bar(
        scr,
        top + 11,
        progress_x,
        progress_width,
        elapsed,
        duration,
        accent_n,
        dim,
    )
    if elapsed is not None and duration and duration > 0:
        pct = max(0.0, min(elapsed / duration, 1.0))
        elapsed_text = _format_time(elapsed)
        duration_text = _format_time(duration)
        _safe_addstr(scr, top + 12, progress_x, elapsed_text, dim)
        _safe_addstr(
            scr,
            top + 12,
            progress_x + progress_width - len(duration_text),
            duration_text,
            dim,
        )
        percent = f"{round(pct * 100):d}%"
        _safe_addstr(scr, top + 12, cx - len(percent) // 2, percent, dim)

    # Queue context doubles as the temporary feedback area after an action.
    if toast_visible:
        if toast_detail:
            headline = _ellipsize(toast_msg, cw)
            detail = _ellipsize(toast_detail, cw)
            _safe_addstr(scr, top + 13, cx - len(headline) // 2, headline, accent)
            _safe_addstr(scr, top + 14, cx - len(detail) // 2, detail, dim)
        else:
            message = f" {_ellipsize(toast_msg, cw - 2)} "
            _safe_addstr(
                scr,
                top + 14,
                max(lm, cx - len(message) // 2),
                message,
                text | curses.A_REVERSE,
            )
    elif next_title:
        _safe_addstr(scr, top + 14, lm, "UP NEXT", accent_n)
        next_track = next_title
        if next_artist:
            next_track = f"{next_track} · {next_artist}"
        next_track = _ellipsize(next_track, cw - 10)
        _safe_addstr(scr, top + 14, lm + 9, next_track, dim)
    else:
        _safe_addstr(scr, top + 14, lm, "QUEUE", accent_n)
        _safe_addstr(scr, top + 14, lm + 7, "End of queue", dim)

    _safe_addstr(scr, top + 15, lm, "─" * cw, bdr)
    playback_controls = "   ".join(
        f"{icon} [{key.upper()}] {description}" for icon, key, description in control_items[:3]
    )
    library_controls = "   ".join(
        f"{icon} [{key.upper()}] {description}" for icon, key, description in control_items[3:]
    )
    _draw_ctrl_line(
        scr,
        top + 16,
        cx - len(playback_controls) // 2,
        playback_controls,
        accent_n,
        dim,
    )
    _draw_ctrl_line(
        scr,
        top + 17,
        cx - len(library_controls) // 2,
        library_controls,
        accent_n,
        dim,
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
