# Timestamped Lyrics Feature

## Overview
The YTM CLI now supports precise lyric synchronization using timestamped lyrics from LRCLIB API, with intelligent fallback to YouTube Music lyrics.

## Implementation Details

### Core Components
- **lyrics_service.py**: Main service module for fetching and parsing timestamped lyrics
- **LyricsService class**: Handles LRCLIB API integration with requests
- **LRCParser class**: Parses LRC format with millisecond precision timestamps
- **Enhanced display_lyrics_with_curses()**: Updated to handle both timestamped and plain text lyrics

### API Integration
- **LRCLIB API**: Free service with 3+ million timestamped lyrics
- **Base URL**: https://lrclib.net/api
- **No API key required**: Simple HTTP requests with user-agent header
- **Endpoints**: /get (exact match), /search (fuzzy search)

### LRC Format Support
- **Format**: `[mm:ss.xxx]lyrics text`
- **Precision**: Supports 2-3 digit centiseconds (hundredths/thousandths)
- **Parsing**: Converts timestamps to seconds as float values
- **Sorting**: Automatically sorted by timestamp for proper playback sync

### User Experience
1. Press 'l' during playback to view lyrics
2. System first tries LRCLIB for timestamped lyrics
3. If found, precise highlighting follows exact playback time
4. If not found, falls back to YouTube Music with estimation
5. Header shows lyrics source: "(LRCLIB)" or "(YouTube Music)"

### Key Functions
- `get_timestamped_lyrics(item)`: Main entry point for fetching lyrics
- `LRCParser.parse_lrc()`: Converts LRC text to (timestamp, text) tuples
- `get_current_line_index()`: Determines which line to highlight based on playback time
- `get_song_metadata_from_item()`: Extracts search parameters from YTM items

### Fallback System
1. **Primary**: LRCLIB exact match by title/artist/album/duration
2. **Secondary**: LRCLIB search by track name
3. **Fallback**: YouTube Music lyrics with time estimation
4. **Graceful degradation**: Always shows something if any lyrics available

### Dependencies
- **requests**: Added to requirements.txt for HTTP API calls
- **re**: For regex parsing of LRC timestamp format
- **typing**: Type hints for better code maintainability

### Configuration Compatibility
- Works with existing mpv integration via IPC socket
- Uses existing `get_mpv_time_position()` function for sync
- Maintains backward compatibility with plain text lyrics display
- Follows existing curses UI patterns and color schemes

## Technical Notes
- Timestamps are precise to milliseconds for smooth synchronization
- Line wrapping preserves timestamp associations for proper highlighting
- Memory efficient: only parses LRC data when timestamped lyrics available
- Error handling: Graceful fallback on API failures or parsing errors
- Network timeout: 10 seconds for API requests to prevent hanging

This feature significantly improves the lyrics experience while maintaining the app's core philosophy of simple, uninterrupted music enjoyment.