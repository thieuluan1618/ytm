# Enhanced Verbose Logging

## Overview

The YTM CLI includes a beautiful, comprehensive verbose logging system that shows exactly what happens behind the scenes during music search, radio generation, and playback.

## Enabling Verbose Mode

```bash
# Search with verbose output
ytm search "song name" --verbose

# With auto-select (non-interactive)
ytm search "song name" --select 1 --verbose

# Save logs to file
ytm search "song name" --select 1 --verbose --log-file debug.log

# Short flags also work
ytm search "song" -s 1 -v

# LLM mode with verbose
ytm llm "play upbeat music" --verbose
```

## What Gets Logged

### 1. Music Search (🔍)
- **Search Query**: The exact search string sent to YouTube Music API
- **API Call**: `ytmusic.search` with parameters
- **Results Count**: Total songs found
- **Filtering**: Number of disliked songs filtered out
- **Results Table**: Formatted table showing:
  - Song title (first 40 chars)
  - Artist name (first 30 chars)
  - Album name (first 30 chars)
  - Duration
  - Top 10 results displayed

### 2. Radio Playlist Generation (📻)
- **Video ID**: The selected song's YouTube video ID
- **API Call**: `ytmusic.get_watch_playlist`
- **Radio Tracks**: Number of tracks returned
- **Dislike Filtering**: Songs filtered from radio
- **Final Count**: Total tracks in generated playlist

### 3. Playlist Composition (📝)
- **Visual Tree**: Hierarchical view of playback queue
- **Current Song**: Highlighted with ► symbol
- **Track List**: Up to 15 tracks shown with title and artist
- **Total Count**: Complete queue size

### 4. Playback Lifecycle (🎵)
- **MPV Start**:
  - Song title and artist
  - Video ID
  - IPC socket path
  - Process ID (PID)
- **MPV Stop**:
  - Exit code
  - Reason (finished, error, user skip)
  - Error details (if any)
- **Song Changes**:
  - Current position in queue (e.g., "3/50")
  - New song title and artist

### 5. User Actions (◆)
- Pause/resume
- Skip forward/backward
- Add to playlist
- Dislike song
- Lyrics display

## Log Icons

- **▶** Step/Action
- **ℹ** Information
- **✓** Success
- **⚠** Warning
- **✗** Error
- **◆** User interaction

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verbose logging enabled
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎵 Searching for: test song

────────────────────────────────────────────────────────────
🔍 Music Search
────────────────────────────────────────────────────────────
13:51:43 ▶ Searching YouTube Music: test song
13:51:43   ℹ API: ytmusic.search
13:51:43   ℹ Params: query=test song, filter=songs
13:51:44   ✓ Found 20 results

────────────────────────────────────────────────────────────
🔍 Search Results
────────────────────────────────────────────────────────────
13:51:44 ▶ Query: test song
13:51:44   ℹ Total results: 20
┏━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┓
┃ # ┃ Title       ┃ Artist    ┃ Album     ┃ Duration ┃
┡━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1 │ Test Song   │ Artist    │ Album     │ 3:45     │
└───┴─────────────┴───────────┴───────────┴──────────┘

────────────────────────────────────────────────────────────
📻 Radio Playlist Generation
────────────────────────────────────────────────────────────
13:51:45 ▶ Video ID: ABC123
13:51:45   ✓ Received 49 radio tracks
13:51:45   ⚠ Filtered 2 disliked song(s)
13:51:45   ✓ Final playlist ready: 48 tracks

────────────────────────────────────────────────────────────
📝 Playlist Composition
────────────────────────────────────────────────────────────
Playback Queue
├── ► 1. Test Song - Artist
├── 2. Similar Song - Another Artist
├── 3. Related Track - Third Artist
└── ... + 45 more tracks

────────────────────────────────────────────────────────────
🎵 MPV Player
────────────────────────────────────────────────────────────
13:51:46 ▶ Starting MPV process
13:51:46   ℹ Title: Test Song
13:51:46   ℹ Artist: Artist
13:51:46   ℹ Video ID: ABC123
13:51:46   ℹ IPC Socket: /tmp/xyz.sock
13:51:46   ✓ MPV started (PID: 12345)
```

## Debugging Use Cases

### 1. Songs Skipping Continuously
```bash
ytm search "problematic song" -s 1 -v --log-file skip.log
```
Check log for:
- MPV exit codes (non-zero indicates errors)
- `yt-dlp` errors in stderr
- Network/streaming issues

### 2. Understanding Radio Generation
```bash
ytm search "seed song" -s 1 -v
```
See:
- How many tracks YouTube Music returns
- Which songs get filtered (dislikes)
- Final playlist composition

### 3. API Call Analysis
```bash
ytm search "query" -v --log-file api.log
```
Track:
- Which API endpoints are called
- Parameters sent
- Response times (via timestamps)

### 4. Playlist Behavior
```bash
ytm playlist play "My Favorites" -v
```
Understand:
- Playlist loading process
- Song order
- Dislike filtering

## Log File Format

When using `--log-file`, logs are saved with:
- Header with start timestamp
- Plain text format (no ANSI colors)
- All verbose output preserved
- One entry per line with timestamp

Example log file entry:
```
=== YTM CLI Verbose Log ===
Started at: 2025-01-18 13:51:42
==================================================

[13:51:43] ▶ Searching YouTube Music: test song
[13:51:43]   ℹ API: ytmusic.search
[13:51:44]   ✓ Found 20 results
```

## Performance Impact

Verbose mode has minimal performance impact:
- **Logging**: Adds <50ms per operation
- **Terminal Output**: Depends on terminal speed
- **File Logging**: Asynchronous, no blocking
- **Search/Playback**: Same speed as normal mode

## Tips

1. **Debugging**: Always use `--log-file` for persistent logs
2. **Performance Testing**: Verbose mode shows exact timing between operations
3. **API Issues**: Check API call parameters in logs
4. **MPV Problems**: Look for exit codes and stderr output
5. **Playlist Analysis**: Tree view shows complete queue structure

## Integration with Other Features

Verbose logging works with:
- ✅ Search mode (`ytm search`)
- ✅ LLM mode (`ytm llm`)
- ✅ Playlist playback (`ytm playlist play`)
- ✅ Auto-select (`--select` flag)
- ✅ Log files (`--log-file`)

## Technical Details

### Implementation
- **Module**: `ytm_cli/verbose_logger.py`
- **Framework**: `rich` library for formatting
- **Components**: Panel, Table, Tree for structured output
- **Timestamps**: HH:MM:SS format
- **File Logging**: UTF-8 encoding with timestamps

### Log Levels
1. **Section**: Major workflow stages
2. **Step**: Individual operations
3. **Info**: Supporting details
4. **Success**: Completed actions
5. **Warning**: Non-critical issues
6. **Error**: Failures and exceptions

## Future Enhancements

Potential improvements:
- [ ] Configurable log levels (INFO, DEBUG, TRACE)
- [ ] JSON output format option
- [ ] Real-time progress bars
- [ ] Network request timing details
- [ ] Memory usage tracking
- [ ] Filter logs by section type

## See Also

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [TESTING.md](TESTING.md) - Testing with verbose mode
- [README.md](README.md) - Main usage documentation
