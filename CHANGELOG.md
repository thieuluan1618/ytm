# Changelog

All notable changes to this project will be documented in this file.

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