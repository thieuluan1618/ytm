# Changelog

All notable changes to this project will be documented in this file.

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