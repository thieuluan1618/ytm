# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.7.3] - 2026-05-17

### Fixed

- **PyPI compatibility**: Lowered `requires-python` from `>=3.14` to `>=3.10` so `uvx ytm-cli` can install the latest release on common Python versions instead of falling back to older compatible releases.

## [0.7.2] - 2026-05-17

### Removed

- **Authentication system**: Full removal of OAuth and browser-based auth flows (`ytm_cli/auth.py` deleted along with the `[auth]` config section, `auth` CLI subcommands, and related tests)

### Changed

- **Config storage**: `config.ini`, `dislikes.json`, and `playlists/` now live under `~/.config/ytm-cli/` instead of the repo root (XDG-style dotfiles)
- **YTMusic client**: Lazy, cached singleton via `get_ytmusic()` — no more per-call `YTMusic()` HTTP sessions
- **uvx behavior**: `uvx ytm-cli` now resolves the latest published version by default (`uv config set --global index-strategy unsafe-first-match`)

### Added

- **Migration script** ([migrate_config.py](migrate_config.py)) to move legacy repo-root config files into `~/.config/ytm-cli/`
- **Release process documentation** ([RELEASING.md](RELEASING.md))

### Fixed

- **`ytmusicapi` dependency restored** — was accidentally dropped from `pyproject.toml` while the import was still in use; first search would have crashed with `ImportError`
- **`DislikeManager` / `PlaylistManager` constructors** now accept an optional path argument again (defaulting to the dotfile location), unbreaking ~50 tests and test isolation
- **`LLMClient` reads config-dir paths** instead of requiring positional args
- **CLI startup**: no more auth initialization delays or `[auth]`-section parsing errors on first run
- **`.gitignore`**: re-added `playlists/` and `dislikes.json` so stale repo-root copies don't get committed during migration
- **Test suite**: repaired after the auth/dotfiles refactor — `test_main.py` patches `get_ytmusic` instead of the removed module-level `ytmusic`; `test_integration.py` no longer imports the deleted `AuthManager`; `test_config.py` / `test_dislikes.py` / `test_playlists.py` assert the new `~/.config/ytm-cli/` paths

## [0.7.1] - 2026-05-17

> ⚠️ **Broken release** — published with the auth-removal refactor but missed the `ytmusicapi` import cleanup and tightened manager-constructor signatures. Use **0.7.2** instead.

## [0.5.0] - 2025-10-27

### Added

- **Easy Setup Scripts**: Cross-platform alias setup for simple `ytm` command
  - `setup_alias.sh` for Linux/macOS (supports zsh, bash, fish shells)
  - `setup_alias.ps1` for Windows PowerShell
  - `setup_alias.bat` for Windows Command Prompt
  - Auto-detects shell configuration and venv path
  - One-command setup for easier installation

- **Automated Dependency Management**: Dependabot integration for automatic updates
  - Weekly dependency update checks every Monday
  - Automatic security vulnerability scanning
  - Pull requests with grouped patch updates
  - Configured via `.github/dependabot.yml`

- **Smart Auto-Selection**: When only one playlist exists, automatically select it
  - Applies to `playlist show`, `playlist play`, and `playlist delete` commands
  - Follows app philosophy: "Keep it simple for the listener to enjoy music"
  - Reduces unnecessary user interactions for single-playlist scenarios

- **Two-Step Dislike System**: Context-aware dislike behavior for better playlist management
  - **From user playlists**: First press 'd' removes from playlist, second press adds to global dislikes
  - **From search/radio**: Direct press 'd' adds to global dislikes and skips
  - Visual feedback with emoji indicators (📝 for playlist removal, 👎 for global dislike)
  - Prevents accidental permanent dislikes from curated playlists

### Enhanced

- **Dependencies**: Updated yt-dlp to 2025.10.22 (fixes songs skipping issues)
- **Documentation**: Major README.md simplification
  - Removed authentication section (feature in development)
  - Updated all examples to use `ytm` alias for cleaner commands
  - Added platform-specific setup instructions
  - Streamlined troubleshooting guide links
- **Documentation**: Enhanced CLAUDE.md with dependency management guidelines
  - Added Dependabot setup instructions
  - Manual update procedures
  - GitHub CLI commands for enabling automation
- **Playlist Management**: Added `remove_song_from_playlist_by_id()` method for video ID-based removal
- **User Experience**: Smart dislike workflow protects user-curated playlists

### Fixed

- **Version Sync**: Fixed pyproject.toml version mismatch (was 0.3.0, now synced to current)
- **Player UI Sync**: Play/pause status now syncs with mpv player UI controls
  - Status display updates when pause/play is controlled via mpv UI clicks
  - Status display updates when using mpv keyboard shortcuts (e.g., 'p' key)
  - Implemented throttled IPC polling (every 0.5 seconds) for performance
  - Maintains responsive CLI controls while adding UI sync capability

### Changed

- **Repository**: Merged develop branch to main with latest features
- **Installation**: Simplified setup process with optional alias configuration

## [0.4.0] - 2025-07-24

### Added

- **Dislike System**: Comprehensive song dislike functionality
  - Press 'd' during playback to dislike current song and skip to next
  - Persistent storage of disliked songs in `dislikes.json`
  - Automatic filtering of disliked songs from:
    - Search results
    - Radio playlists
    - Local playlist playback
  - Privacy-focused: `dislikes.json` added to `.gitignore`

### Enhanced

- **Playback Controls**: Added 'd' key for dislike functionality with immediate skip
- **User Experience**: Fun emoji icons for all playback controls (space: ⏯️, n: ⏭️, b: ⏮️, l: 📜, a: ➕, d: 👎, q: 🚪)
- **Smart Filtering**: Disliked songs are intelligently filtered across the entire application
- **Documentation**: Updated help text and controls display to include new dislike functionality

### Changed

- Enhanced UI controls display with visual emoji indicators
- Improved filtering system that works seamlessly across search, radio, and playlists

## [0.3.0] - 2025-07-20

### Added

- **Playlist Management**: Complete local playlist system
  - Create, view, play, and delete playlists via CLI commands
  - Add songs to playlists during search selection (press 'a')
  - **NEW**: Add current song to playlist during playback (press 'a')
  - Interactive playlist selection UI with option to create new playlists
  - Local storage in JSON format with metadata
  - Cross-platform safe filenames and UTF-8 encoding

### Enhanced

- **Playback Controls**: Added 'a' key to add current song to playlist without interrupting music
- **User Experience**: Non-disruptive playlist management follows app philosophy of simple music enjoyment
- **Documentation**: Updated help text and controls display to include new 'a' key functionality
- **Architecture**: Improved modular structure with dedicated playlist management module

### Changed

- Modular architecture: Split functionality across focused modules (main.py, player.py, ui.py, playlists.py, config.py)
- Updated CLI help and documentation to reflect new playlist features
- Enhanced player status display with new controls

## [0.2.0] - 2025-07-17

### Changed

- Minor version bump.

## [0.1.0] - 2025-07-13

### Added

- Interactive search results with 'j' and 'k' navigation.
- Playback controls: 'n' (next), 'b' (previous), 'q' (quit).
- Radio mode: automatically plays a playlist based on the selected song.
- Graceful exit with Ctrl+C.
- Command-line argument for search queries.
- README with a screenshot.
