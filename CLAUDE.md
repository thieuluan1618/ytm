# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based YouTube Music CLI tool that provides an interactive terminal interface for searching, playing, and controlling music from YouTube Music. The application uses mpv as the media player backend and provides keyboard controls for playback.

**Core Philosophy**: Keep it simple for the listener to enjoy music. Features should be intuitive, accessible during playback, and not interrupt the listening experience.

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
python -m vena vena
source venv/bin/activate  # macOS/Linux
# .\venv\Scripts\activate  # Windows PowerShell
# venv\Scripts\activate.bat # Windows Command Prompt

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Interactive mode (search prompt)
python -m ytm_cli

# Direct search from command line
python -m ytm_cli "song name or artist"

# Note: Legacy ytm-cli.py still works for backward compatibility
```

### Dependencies Management

```bash
# Update requirements.txt after adding new dependencies
pip freeze > requirements.txt
```

## Architecture

### Core Components

- **Modular architecture**: Organized into focused modules (main.py, player.py, ui.py, playlists.py, dislikes.py, config.py)
- **YTMusic Integration**: Uses `ytmusicapi` library for YouTube Music API access
- **Media Player**: Integrates with mpv via subprocess and IPC socket communication
- **Terminal UI**: Prioritizes `curses` for all text display and interactive interfaces, with `rich` as secondary for simple formatting

### Key Functions

- `search_and_play()`: Main entry point for search and playback workflow
- `selection_ui()`: Curses-based interactive song selection interface
- `play_music_with_controls()`: Media playback with keyboard controls (space=pause, n=next, b=previous, l=lyrics, a=add to playlist, d=dislike, q=quit)
- `send_mpv_command()`: IPC communication with mpv player via Unix socket

### Configuration

Configuration is managed through `config.ini`:

- `[general]`: Display settings (songs*to_display, show*\* flags)
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

Version is defined as `__version__ = "0.3.0"` in the main script. Use `bump2version` for version updates as indicated in requirements.txt.

## Commit Message Standards

This project follows **conventional commits** format for consistency and automated tooling:

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: New feature for the user
- **fix**: Bug fix for the user
- **docs**: Documentation changes
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **test**: Adding or modifying tests
- **chore**: Changes to build process, dependencies, or tooling
- **perf**: Performance improvements
- **style**: Code style changes (formatting, missing semi-colons, etc.)

### Examples

```
feat: add comprehensive dislike functionality with emoji controls
fix: update bumpversion config to use correct version file
docs: update CLAUDE.md with commit message guidelines
refactor: split ytm-cli.py into modular package structure
chore: add curl_command.txt to .gitignore
```

### Scope (Optional)

- **ui**: User interface changes
- **auth**: Authentication system
- **player**: Media player functionality
- **playlist**: Playlist management
- **config**: Configuration system

### Special Cases

- **Version bumps**: Use `chore: bump version X.Y.Z → A.B.C`
- **Breaking changes**: Add `BREAKING CHANGE:` in footer
- **Issue references**: Add `Closes #123` in footer

## Authentication

The application supports optional authentication via OAuth or browser method:

### OAuth Authentication (Recommended)

```bash
python -m ytm_cli auth setup-oauth    # Interactive OAuth setup
python -m ytm_cli auth scan            # Scan for credential files
python -m ytm_cli auth manual          # Show setup manual
```

**Note**: New OAuth apps may encounter "Google verification process" errors. This is normal and can be resolved by:

1. Adding test users to the OAuth consent screen
2. Using browser authentication as alternative
3. Run `python -m ytm_cli auth troubleshoot` for detailed solutions

### Browser Authentication (Alternative)

```bash
python -m ytm_cli auth setup-browser   # Setup using browser headers
```

### Authentication Management

```bash
python -m ytm_cli auth status          # Check auth status
python -m ytm_cli auth disable         # Disable authentication
```

## Local Playlists

The application supports local playlist management for organizing favorite songs:

### Playlist Management

```bash
python -m ytm_cli playlist list        # List all playlists
python -m ytm_cli playlist create      # Create new playlist
python -m ytm_cli playlist show <name> # View playlist contents
python -m ytm_cli playlist play <name> # Play entire playlist
python -m ytm_cli playlist delete <name> # Delete playlist
```

### Adding Songs to Playlists

**During Search/Selection:**

1. Search for music: `python -m ytm_cli "song name"`
2. Navigate search results with ↑↓ or j/k keys
3. Press `'a'` to add current song to a playlist
4. Choose existing playlist or create new one

**During Playback (New Feature):**

1. While listening to any song, press `'a'` to add it to a playlist
2. Interactive menu appears without stopping playback
3. Select existing playlist or create new one
4. Song added seamlessly, music continues

This follows the app's philosophy of keeping music enjoyment simple and uninterrupted.

### Playlist Storage

- Local storage in `playlists/` directory (JSON format)
- Cross-platform safe filenames
- UTF-8 encoding for international characters
- Metadata includes: title, artist, album, duration, timestamps
- Added to `.gitignore` for privacy

### Configuration

Playlist settings in `config.ini`:

```ini
[playlists]
directory = playlists      # Storage location
max_playlists = 100       # Future limit (not enforced yet)
auto_backup = false       # Future backup feature
```

## Song Dislike System

The application includes a comprehensive dislike system to filter out unwanted songs:

### Dislike Functionality

**Two-Step Dislike System:**

When playing from a **user playlist**:
1. First press `'d'`: Removes song from current playlist only
2. Second press `'d'`: Adds song to global dislikes (permanent filtering)
3. Visual feedback guides user through the process

When playing from **search/radio**:
1. Press `'d'`: Directly adds to global dislikes and skips song

**Smart Filtering:**

- Disliked songs are automatically filtered from:
  - Search results
  - Radio playlist generation
  - Local playlist playback
- Real-time feedback shows "Filtered out X disliked song(s)" when applicable
- Two-step process prevents accidental permanent dislikes from playlists

### Dislike Storage

- **File Location**: `dislikes.json` in project root
- **Format**: JSON with metadata (title, artist, videoId, album, timestamp)
- **Privacy**: File added to `.gitignore` to keep personal preferences private
- **Persistence**: Dislikes persist across application restarts and updates

### Key Features

- **Smart Two-Step Process**: Context-aware dislike behavior (playlist vs. search/radio)
- **Playlist Protection**: First removes from playlist, requires confirmation for global dislike
- **Comprehensive Filtering**: Works across all song discovery methods
- **Non-Disruptive**: Follows app philosophy of simple, uninterrupted music enjoyment
- **Visual Feedback**: Clear confirmation with emoji indicators (📝 for playlist removal, 👎 for global dislike)

This system allows users to gradually curate their music experience while protecting against accidental permanent dislikes from playlists.

## Design Principles

When adding new features, follow these principles:

1. **Simplicity First**: Features should be discoverable and intuitive. Single-key shortcuts during playback are preferred.
2. **Non-Disruptive**: New functionality should not interrupt music playback or require complex workflows.
3. **Consistent UI**: Use curses for interactive interfaces, maintain vim-like navigation (j/k keys).
4. **Quick Access**: Important features should be accessible during playback with simple key presses.
5. **Clear Feedback**: Provide immediate visual confirmation of actions without blocking the user.

## Key Bindings Philosophy

- **During Playback**: Single letter keys for immediate actions (space, n, b, l, a, d, q)
- **During Selection**: Same vim-like navigation everywhere (j/k, ↑↓, Enter, q)
- **Consistent**: Same keys do the same things across different screens
- **Memorable**: Use logical letters (a=add, d=dislike, l=lyrics, q=quit, etc.)
