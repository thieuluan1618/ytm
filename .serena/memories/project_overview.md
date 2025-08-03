# Project Overview

## Purpose
YouTube Music CLI (ytm) is a Python-based terminal application that provides an interactive interface for searching, playing, and controlling music from YouTube Music. The application uses mpv as the media player backend and provides keyboard controls for playback.

## Core Philosophy
Keep it simple for the listener to enjoy music. Features should be intuitive, accessible during playback, and not interrupt the listening experience.

## Tech Stack
- **Python 3.8+ to 3.13.5** (based on CI configuration)
- **ytmusicapi** - YouTube Music API client
- **rich** - Terminal formatting and colors
- **mpv** - Media player (system dependency, accessed via subprocess/IPC)
- **pyperclip** - Clipboard operations
- **bump2version** - Version management
- **curses** - Built-in Python library for terminal UI (preferred for all interactive interfaces)

## Key Features
- Interactive terminal interface for music search and selection
- Local playlist management (JSON storage)
- Comprehensive dislike system with smart filtering
- OAuth and browser-based authentication
- MPV integration with IPC socket communication
- Vim-like navigation (j/k keys) throughout the interface
- Real-time keyboard controls during playback

## Architecture
Modular design with focused components:
- `main.py` - CLI entry point and command routing
- `player.py` - MPV integration and playback controls
- `ui.py` - Curses-based terminal interfaces
- `auth.py` - Authentication management (OAuth/browser)
- `playlists.py` - Local playlist functionality
- `dislikes.py` - Song dislike and filtering system
- `config.py` - Configuration management
- `utils.py` - Utility functions