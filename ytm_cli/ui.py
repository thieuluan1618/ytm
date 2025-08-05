"""User interface components for YTM CLI"""

import curses
import os
import time
from curses import wrapper

from .playlists import playlist_manager


def display_lyrics_with_curses(
    lyrics_data, title, socket_path=None, get_mpv_time_position_func=None
):
    """Display lyrics using curses with live highlighting

    Args:
        lyrics_data: Either string (plain lyrics) or dict with timestamped lyrics
        title: Song title
        socket_path: MPV IPC socket path
        get_mpv_time_position_func: Function to get current playback time
    """

    def lyrics_ui(stdscr):
        curses.curs_set(0)  # Hide cursor
        curses.use_default_colors()

        # Define color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)  # Header
        curses.init_pair(2, curses.COLOR_WHITE, -1)  # Lyrics text
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Footer/instructions
        curses.init_pair(4, curses.COLOR_GREEN, -1)  # Highlight
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Current line highlight

        header_color = curses.color_pair(1)
        text_color = curses.color_pair(2)
        footer_color = curses.color_pair(3)
        current_line_color = curses.color_pair(5)

        # Handle both plain text and timestamped lyrics
        timestamped_lyrics = []
        lyrics_source = ""

        if isinstance(lyrics_data, dict):
            # Timestamped lyrics data
            if lyrics_data.get("parsed_lyrics"):
                timestamped_lyrics = lyrics_data["parsed_lyrics"]
                lyrics_text = lyrics_data.get("synced_lyrics", "") or lyrics_data.get(
                    "plain_lyrics", ""
                )
                lyrics_source = f" ({lyrics_data.get('source', 'Unknown')})"
            else:
                lyrics_text = lyrics_data.get("plain_lyrics", "") or lyrics_data.get(
                    "synced_lyrics", ""
                )
        else:
            # Plain text lyrics
            lyrics_text = lyrics_data or ""

        # Prepare lyrics lines
        if timestamped_lyrics:
            # Use timestamped lyrics directly (already parsed)
            lines = [text for _, text in timestamped_lyrics]
        else:
            # Split plain text into lines
            lines = [line.strip() for line in lyrics_text.split("\n")]

        max_y, max_x = stdscr.getmaxyx()

        # Wrap long lines to fit terminal width
        wrapped_lines = []
        timestamp_map = {}  # Map wrapped line index to original timestamp

        for orig_idx, line in enumerate(lines):
            if len(line) <= max_x - 4:  # Leave margin
                wrapped_lines.append(line)
                if timestamped_lyrics and orig_idx < len(timestamped_lyrics):
                    timestamp_map[len(wrapped_lines) - 1] = timestamped_lyrics[orig_idx][0]
            else:
                # Simple word wrapping
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= max_x - 4:
                        current_line += " " + word if current_line else word
                    else:
                        wrapped_lines.append(current_line)
                        if timestamped_lyrics and orig_idx < len(timestamped_lyrics):
                            timestamp_map[len(wrapped_lines) - 1] = timestamped_lyrics[orig_idx][0]
                        current_line = word
                if current_line:
                    wrapped_lines.append(current_line)
                    if timestamped_lyrics and orig_idx < len(timestamped_lyrics):
                        timestamp_map[len(wrapped_lines) - 1] = timestamped_lyrics[orig_idx][0]

        lines = wrapped_lines
        scroll_pos = 0
        content_height = max_y - 4  # Reserve space for header and footer

        while True:
            stdscr.erase()

            # Calculate current highlighted line based on playback time
            current_highlighted_line = -1
            if socket_path and get_mpv_time_position_func:
                current_time = get_mpv_time_position_func(socket_path)

                if timestamped_lyrics and current_time > 0:
                    # Use precise timestamps for highlighting
                    for line_idx, timestamp in timestamp_map.items():
                        if current_time >= timestamp:
                            current_highlighted_line = line_idx
                        else:
                            break
                elif current_time > 0:
                    # Fallback to estimation for plain text lyrics
                    non_empty_lines = [i for i, line in enumerate(lines) if line.strip()]
                    line_duration = 3.0  # Assume 3 seconds per line on average
                    if non_empty_lines:
                        estimated_line_index = int(current_time / line_duration)
                        if estimated_line_index < len(non_empty_lines):
                            current_highlighted_line = non_empty_lines[estimated_line_index]

            # Auto-scroll to follow highlighted line
            if current_highlighted_line >= 0:
                if current_highlighted_line < scroll_pos:
                    scroll_pos = max(0, current_highlighted_line - 2)
                elif current_highlighted_line >= scroll_pos + content_height:
                    scroll_pos = max(
                        0,
                        min(
                            current_highlighted_line - content_height + 3,
                            len(lines) - content_height,
                        ),
                    )

            # Header
            header_text = f"🎵 {title}{lyrics_source}"
            border = "═" * (max_x - 2)

            stdscr.addstr(0, 0, border[: max_x - 1], header_color)
            if len(header_text) < max_x - 1:
                stdscr.addstr(1, (max_x - len(header_text)) // 2, header_text, header_color)
            else:
                stdscr.addstr(1, 0, header_text[: max_x - 1], header_color)
            stdscr.addstr(2, 0, border[: max_x - 1], header_color)

            # Display lyrics content
            for i in range(content_height):
                line_idx = scroll_pos + i
                if line_idx < len(lines):
                    line = lines[line_idx]
                    if line:
                        # Highlight the current line
                        if line_idx == current_highlighted_line:
                            stdscr.addstr(3 + i, 2, f"♪ {line[: max_x - 5]}", current_line_color)
                        else:
                            stdscr.addstr(3 + i, 2, line[: max_x - 3], text_color)
                    # Empty lines create natural spacing

            # Footer with instructions
            footer_y = max_y - 1
            total_lines = len(lines)

            if total_lines > content_height:
                # Show scroll info with time position
                progress = f"[{scroll_pos + 1}-{min(scroll_pos + content_height, total_lines)}/{total_lines}]"
                time_info = ""
                if socket_path:
                    current_time = get_mpv_time_position_func(socket_path)
                    time_info = f" | {int(current_time // 60)}:{int(current_time % 60):02d}"
                instructions = f"j/k: scroll | q: back{time_info} | {progress}"
            else:
                instructions = "q: back to player"

            if len(instructions) < max_x - 1:
                stdscr.addstr(footer_y, 0, instructions[: max_x - 1], footer_color)

            stdscr.refresh()

            # Handle input with timeout for live updates
            stdscr.timeout(500)  # 500ms timeout
            key = stdscr.getch()

            if key == ord("q"):
                break
            elif key == ord("j") or key == curses.KEY_DOWN:
                if scroll_pos + content_height < len(lines):
                    scroll_pos += 1
            elif key == ord("k") or key == curses.KEY_UP:
                if scroll_pos > 0:
                    scroll_pos -= 1
            if key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(scroll_pos + content_height, len(lines) - content_height)
                scroll_pos = max(0, scroll_pos)
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(scroll_pos - content_height, 0)
            elif key == curses.KEY_HOME:  # Home - go to top
                scroll_pos = 0
            elif key == curses.KEY_END:  # End - go to bottom
                scroll_pos = max(len(lines) - content_height, 0)

    return wrapper(lyrics_ui)


def selection_ui(stdscr, results, query, songs_to_display):
    """Interactive song selection UI using curses"""

    curses.curs_set(0)
    curses.use_default_colors()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_YELLOW, -1)  # Selected item
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # Instructions
    curses.init_pair(3, curses.COLOR_GREEN, -1)  # Success messages
    yellow = curses.color_pair(1)
    cyan = curses.color_pair(2)
    green = curses.color_pair(3)

    current_selection = 0
    status_message = ""
    status_timer = 0

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # Header
        stdscr.addstr(0, 0, f"🎵 Search Results for: {query}\n")

        # Instructions
        instructions = "Enter: play | a: add to playlist | q: quit | ↑↓/jk: navigate"
        stdscr.addstr(1, 0, instructions[: max_x - 1], cyan)
        stdscr.addstr(2, 0, "")  # Empty line

        # Song list
        for i, song in enumerate(results[:songs_to_display]):
            title = song["title"]
            artist = song["artists"][0]["name"]
            line = f"[{i + 1}] {title} - {artist}"

            # Truncate if too long
            if len(line) > max_x - 3:
                line = line[: max_x - 6] + "..."

            try:
                if i == current_selection:
                    stdscr.addstr(i + 3, 0, f"> {line}", yellow)
                else:
                    stdscr.addstr(i + 3, 0, f"  {line}")
            except curses.error:
                # Handle Unicode or display issues by encoding to ASCII with error handling
                safe_line = line.encode("ascii", "replace").decode("ascii")
                if i == current_selection:
                    stdscr.addstr(i + 3, 0, f"> {safe_line}", yellow)
                else:
                    stdscr.addstr(i + 3, 0, f"  {safe_line}")

        # Status message (temporary feedback)
        if status_message and time.time() - status_timer < 3:
            status_y = min(songs_to_display + 4, max_y - 1)
            stdscr.addstr(status_y, 0, status_message[: max_x - 1], green)
        elif time.time() - status_timer >= 3:
            status_message = ""

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
            # Add to playlist functionality
            selected_song = results[current_selection]
            if add_song_to_playlist_ui(stdscr, selected_song):
                status_message = f"✅ Added '{selected_song['title']}' to playlist!"
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


def display_player_status(title, is_paused):
    """Display player status with centered text that adapts to terminal width"""
    # Clear screen
    os.system("clear" if os.name == "posix" else "cls")

    # Get terminal dimensions
    try:
        terminal_size = os.get_terminal_size()
        width = terminal_size.columns
    except OSError:
        width = 80  # fallback

    # Status and title
    status = "⏸️ Paused" if is_paused else "▶️ Playing"
    status_line = f"{status}: {title}"

    # Controls text
    controls = "  ⏮️ (b)  ⏯️ (space)  ⏭️ (n)  📜 (l)  ❤️ (a)    👎 (d)    🚪 (q)"

    # Center the text
    print()  # Empty line
    if len(status_line) <= width:
        print(status_line.center(width))
    else:
        print(status_line[:width])

    print()  # Empty line
    if len(controls) <= width:
        print(controls.center(width))
    else:
        # Word wrap if too long
        words = controls.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) <= width:
                current_line += " " + word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for line in lines:
            print(line.center(width))
