# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based YouTube Music CLI tool that provides an interactive terminal interface for searching, playing, and controlling music from YouTube Music. The application uses mpv as the media player backend and provides keyboard controls for playback.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# .\venv\Scripts\activate  # Windows PowerShell
# venv\Scripts\activate.bat # Windows Command Prompt

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Interactive mode (search prompt)
python ytm-cli.py

# Direct search from command line
python ytm-cli.py "song name or artist"
```

### Dependencies Management
```bash
# Update requirements.txt after adding new dependencies
pip freeze > requirements.txt
```

## Architecture

### Core Components

- **Single-file architecture**: All functionality is contained in `ytm-cli.py`
- **YTMusic Integration**: Uses `ytmusicapi` library for YouTube Music API access
- **Media Player**: Integrates with mpv via subprocess and IPC socket communication
- **Terminal UI**: Uses `curses` for interactive song selection and `rich` for formatted output

### Key Functions

- `search_and_play()`: Main entry point for search and playback workflow
- `selection_ui()`: Curses-based interactive song selection interface  
- `play_music_with_controls()`: Media playback with keyboard controls (space=pause, n=next, b=previous, q=quit)
- `send_mpv_command()`: IPC communication with mpv player via Unix socket

### Configuration

Configuration is managed through `config.ini`:
- `[general]`: Display settings (songs_to_display, show_* flags)
- `[mpv]`: MPV player flags (e.g., --no-video for audio-only playback)

### Control Flow

1. Search query input (CLI arg or interactive prompt)
2. YTMusic API search for songs
3. Curses-based selection UI with vim-like navigation (j/k keys)
4. Selected song triggers radio playlist generation
5. MPV playback with real-time keyboard controls via IPC socket
6. Automatic progression through radio playlist

### External Dependencies

- **mpv**: Must be installed system-wide for media playback
- **ytmusicapi**: YouTube Music API client
- **rich**: Terminal formatting and colors
- **curses**: Built-in Python library for terminal UI

## Version Management

Version is defined as `__version__ = "0.2.0"` in the main script. Use `bump2version` for version updates as indicated in requirements.txt.