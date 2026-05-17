# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based YouTube Music CLI tool that provides an interactive terminal interface for searching, playing, and controlling music from YouTube Music. The application uses mpv as the media player backend and provides keyboard controls for playback.

**Core Philosophy**: Keep it simple for the listener to enjoy music. Features should be intuitive, accessible during playback, and not interrupt the listening experience.

## Development Commands

### Environment Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install runtime + dev deps from pyproject.toml + uv.lock
uv sync --group dev

# Run any tool/script through the synced env
uv run ytm-cli "song"
uv run pytest
uv run ruff check ytm_cli/ tests/
```

Or with plain pip:

```bash
python -m venv venv
source venv/bin/activate
pip install .                     # runtime deps from pyproject.toml
pip install '.[dev]' || true      # if you need test/lint extras
```

> **Platform support:** Linux, macOS, and WSL2 only. The codebase uses
> POSIX-only modules (`termios`, `tty`, `fcntl`) and will not import on
> native Windows — Windows users should run the project under WSL2.

### Quick Setup (Recommended)

For easier access, set up the `ytm` command alias.

#### Linux / macOS / WSL2

Supports: **zsh**, **bash**, **fish** shells.

```bash
# Run the setup script
./setup_alias.sh

# Reload your shell configuration
source ~/.zshrc                       # for zsh
source ~/.bashrc                      # for bash
source ~/.config/fish/config.fish     # for fish

# Now you can use ytm from anywhere
ytm "song name"
ytm
```

**What it does:**
- Auto-detects your shell (zsh, bash, or fish)
- Creates a `ytm` alias in your shell config
- Activates the project's virtualenv on call
- Forwards arguments to `python -m ytm_cli`
- Works from any directory

### Running the Application

```bash
# Using uv (recommended — no manual venv setup needed)
uv run ytm-cli
uv run ytm-cli "song name or artist"
uv run ytm-cli search "song name" --select 1

# Or using python directly (requires venv activated)
python -m ytm_cli
python -m ytm_cli "song name or artist"
python -m ytm_cli search "song name" --select 1

# Non-interactive mode with verbose logging
python -m ytm_cli search "artist name" --select 1 --verbose

# Verbose logging to file (for debugging playback issues)
python -m ytm_cli search "song" --select 1 --verbose --log-file debug.log

# Short form flags also work
python -m ytm_cli search "song" -s 1 --verbose
```

### Dependencies Management

#### Manual Updates

```bash
# Add a runtime dep (writes to pyproject.toml + uv.lock)
uv add some-package

# Add a dev-only dep
uv add --group dev some-package

# Refresh the lockfile / pull updates
uv sync --upgrade

# Inspect outdated packages
uv pip list --outdated
```

#### Automated Updates (Dependabot)

This project uses **GitHub Dependabot** for automatic dependency updates:

**Configuration**: `.github/dependabot.yml`

**Schedule**:
- Runs every **Monday at 9:00 AM UTC**
- Automatically creates Pull Requests for outdated dependencies
- Groups patch updates together to reduce PR noise
- Ignores major version updates to prevent breaking changes

**Features**:
- Security vulnerability scanning
- Automated security fix PRs
- Weekly version update checks
- PR labels: `dependencies`, `automated`
- Follows conventional commit format (`chore:` prefix)

**Enable Dependabot via GitHub CLI**:
```bash
# Enable vulnerability alerts
gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts

# Enable automated security fixes
gh api -X PUT repos/{owner}/{repo}/automated-security-fixes

# Verify status
gh api repos/{owner}/{repo}/vulnerability-alerts
```

**Manual Trigger**:
- Visit: `https://github.com/{owner}/{repo}/network/updates`
- Click "Check for updates" button to trigger immediate scan

**Benefits**:
- Zero maintenance overhead
- Keeps dependencies secure and up-to-date
- Review and merge PRs at your convenience
- Automatic rollback if tests fail

## Usage Modes

### Interactive Mode (Default)

The default mode presents a curses-based UI for browsing and selecting songs:

- Search results displayed in a scrollable list
- Navigate with arrow keys (↑↓) or vim-style (j/k)
- Press Enter to play selected song with auto-generated radio
- Press 'a' to add song to playlist
- Press 'q' to quit

### Non-Interactive Mode

For automation, scripting, or quick playback without manual selection:

```bash
python -m ytm_cli search "query" --select N
```

**Features:**
- **--select N** or **-s N**: Auto-select song number N (1-based index) from search results
- **--verbose**: Enable detailed logging showing API calls, filtering, and playlist generation
- **--log-file FILE**: Write verbose logs to file for debugging (requires --verbose)
- Bypasses curses UI entirely
- Perfect for scripts, cron jobs, or testing
- Still supports all playback controls once music starts

**Verbose Logging Details:**
When enabled, shows:
- Search API queries and result counts
- Disliked song filtering statistics
- Radio playlist generation info
- MPV process lifecycle (PID, exit codes, errors)
- Song playback progression with timestamps
- Logs written to both stdout and file (if --log-file specified)

**Use Cases:**
- Quick testing: `python -m ytm_cli search "test song" -s 1 --verbose`
- Scripting: Auto-play first result without user interaction
- CI/CD: Automated testing of playback functionality
- Debugging playback issues: `python -m ytm_cli search "song" -s 1 --verbose --log-file debug.log`
- Troubleshooting skipping songs: Check log file for MPV exit codes and errors

## Architecture

### Core Components

- **Modular architecture**: Organized into focused modules (main.py, player.py, ui.py, playlists.py, dislikes.py, config.py)
- **YTMusic Integration**: Uses YouTube Music's public API (no auth required)
- **Media Player**: Integrates with mpv via subprocess and IPC socket communication
- **Terminal UI**: Prioritizes `curses` for all text display and interactive interfaces, with `rich` as secondary for simple formatting

### Key Functions

- `search_and_play()`: Main entry point for search and playback workflow
- `selection_ui()`: Curses-based interactive song selection interface
- `play_music_with_controls()`: Media playback with keyboard controls (space=pause, n=next, b=previous, l=lyrics, a=add to playlist, d=dislike, q=quit)
- `display_lyrics_with_curses()`: Synced lyrics viewer with three-state highlighting (active/past/future), auto-scroll centering, and manual scroll override
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
- **rich**: Terminal formatting and colors
- **curses**: Built-in Python library for terminal UI

## Version Management

Version is defined as `__version__` in `ytm_cli/__init__.py` and `pyproject.toml`. Use `bump2version` (`uvx bump2version patch|minor|major`) for synchronized version bumps; the rules are in `.bumpversion.cfg`.

For the complete release process, see [RELEASING.md](RELEASING.md).

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
- **player**: Media player functionality
- **playlist**: Playlist management
- **config**: Configuration system

### Special Cases

- **Version bumps**: Use `chore: bump version X.Y.Z → A.B.C`
- **Breaking changes**: Add `BREAKING CHANGE:` in footer
- **Issue references**: Add `Closes #123` in footer

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
- **During Lyrics**: j/k scroll, space re-enables auto-scroll, q/Esc exits back to player
- **Consistent**: Same keys do the same things across different screens
- **Memorable**: Use logical letters (a=add, d=dislike, l=lyrics, q=quit, etc.)
