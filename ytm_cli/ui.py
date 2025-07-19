"""User interface components for YTM CLI"""

import curses
from curses import wrapper
import time
import json
import os

from .player import get_mpv_time_position


def display_lyrics_with_curses(lyrics_text, title, socket_path=None):
    """Display lyrics using curses with live highlighting"""
    def lyrics_ui(stdscr):
        curses.curs_set(0)  # Hide cursor
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Header
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Lyrics text
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # Footer/instructions
        curses.init_pair(4, curses.COLOR_GREEN, -1)   # Highlight
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Current line highlight
        
        HEADER_COLOR = curses.color_pair(1)
        TEXT_COLOR = curses.color_pair(2)
        FOOTER_COLOR = curses.color_pair(3)
        HIGHLIGHT_COLOR = curses.color_pair(4)
        CURRENT_LINE_COLOR = curses.color_pair(5)
        
        # Prepare lyrics lines
        lines = [line.strip() for line in lyrics_text.split('\n')]
        max_y, max_x = stdscr.getmaxyx()
        
        # Wrap long lines to fit terminal width
        wrapped_lines = []
        for line in lines:
            if len(line) <= max_x - 4:  # Leave margin
                wrapped_lines.append(line)
            else:
                # Simple word wrapping
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= max_x - 4:
                        current_line += " " + word if current_line else word
                    else:
                        wrapped_lines.append(current_line)
                        current_line = word
                if current_line:
                    wrapped_lines.append(current_line)
        
        lines = wrapped_lines
        scroll_pos = 0
        content_height = max_y - 4  # Reserve space for header and footer
        start_time = time.time()
        
        # Estimate line timing (rough approximation)
        non_empty_lines = [i for i, line in enumerate(lines) if line.strip()]
        line_duration = 3.0  # Assume 3 seconds per line on average
        
        while True:
            stdscr.erase()
            
            # Calculate current highlighted line based on playback time
            current_highlighted_line = -1
            if socket_path:
                current_time = get_mpv_time_position(socket_path)
                if current_time > 0 and non_empty_lines:
                    # Estimate which line should be highlighted
                    estimated_line_index = int(current_time / line_duration)
                    if estimated_line_index < len(non_empty_lines):
                        current_highlighted_line = non_empty_lines[estimated_line_index]
            
            # Auto-scroll to follow highlighted line
            if current_highlighted_line >= 0:
                if current_highlighted_line < scroll_pos:
                    scroll_pos = max(0, current_highlighted_line - 2)
                elif current_highlighted_line >= scroll_pos + content_height:
                    scroll_pos = min(current_highlighted_line - content_height + 3, len(lines) - content_height)
                    if scroll_pos < 0:
                        scroll_pos = 0
            
            # Header
            header_text = f"🎵 {title}"
            border = "═" * (max_x - 2)
            
            stdscr.addstr(0, 0, border[:max_x-1], HEADER_COLOR)
            if len(header_text) < max_x - 1:
                stdscr.addstr(1, (max_x - len(header_text)) // 2, header_text, HEADER_COLOR)
            else:
                stdscr.addstr(1, 0, header_text[:max_x-1], HEADER_COLOR)
            stdscr.addstr(2, 0, border[:max_x-1], HEADER_COLOR)
            
            # Display lyrics content
            for i in range(content_height):
                line_idx = scroll_pos + i
                if line_idx < len(lines):
                    line = lines[line_idx]
                    if line:
                        # Highlight the current line
                        if line_idx == current_highlighted_line:
                            stdscr.addstr(3 + i, 2, f"♪ {line[:max_x-5]}", CURRENT_LINE_COLOR)
                        else:
                            stdscr.addstr(3 + i, 2, line[:max_x-3], TEXT_COLOR)
                    # Empty lines create natural spacing
            
            # Footer with instructions
            footer_y = max_y - 1
            total_lines = len(lines)
            
            if total_lines > content_height:
                # Show scroll info with time position
                progress = f"[{scroll_pos + 1}-{min(scroll_pos + content_height, total_lines)}/{total_lines}]"
                time_info = ""
                if socket_path:
                    current_time = get_mpv_time_position(socket_path)
                    time_info = f" | {int(current_time//60)}:{int(current_time%60):02d}"
                instructions = f"j/k: scroll | q: back{time_info} | {progress}"
            else:
                instructions = "q: back to player"
            
            if len(instructions) < max_x - 1:
                stdscr.addstr(footer_y, 0, instructions[:max_x-1], FOOTER_COLOR)
            
            stdscr.refresh()
            
            # Handle input with timeout for live updates
            stdscr.timeout(500)  # 500ms timeout
            key = stdscr.getch()
            
            if key == ord('q'):
                break
            elif key == ord('j') or key == curses.KEY_DOWN:
                if scroll_pos + content_height < len(lines):
                    scroll_pos += 1
            elif key == ord('k') or key == curses.KEY_UP:
                if scroll_pos > 0:
                    scroll_pos -= 1
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(scroll_pos + content_height, len(lines) - content_height)
                if scroll_pos < 0:
                    scroll_pos = 0
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
    
    # Define color pair 1: yellow text, default background
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    YELLOW = curses.color_pair(1)

    current_selection = 0

    while True:
        stdscr.erase()
        stdscr.addstr(0, 0, f"🎵 Search Results for: {query}\n\n")

        for i, song in enumerate(results[:songs_to_display]):
            title = song['title']
            artist = song['artists'][0]['name']
            line = f"[{i+1}] {title} - {artist}"

            if i == current_selection:
                stdscr.addstr(i + 2, 0, f"> {line}", YELLOW)
            else:
                stdscr.addstr(i + 2, 0, f"  {line}")

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_DOWN, ord('j')):
            current_selection = (current_selection + 1) % songs_to_display
        elif key in (curses.KEY_UP, ord('k')):
            current_selection = (current_selection - 1 + songs_to_display) % songs_to_display
        elif key in (ord('\n'), 10, 13):
            return current_selection
        elif key == ord('q'):
            return None
        elif ord('1') <= key <= ord(str(min(9, songs_to_display))):
            return key - ord('1')


def display_player_status(title, is_paused):
    """Display player status with centered text that adapts to terminal width"""
    # Clear screen
    os.system('clear' if os.name == 'posix' else 'cls')
    
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
    controls = "space: play/pause, n: next song, b: previous song, l: lyrics, q: quit to search"
    
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