# Pygame Fallback Player Testing

## Overview

The CLI now has comprehensive logging for pygame fallback playback errors. This document describes the testing approach and how to verify the pygame fallback works correctly in CLI mode.

## Changes Made

### 1. Enhanced Error Logging in Pygame Player
**File:** `ytm_cli/tui/pygame_player.py`

Added logging to all error handling paths:
- Initialization failures
- Stream URL extraction errors
- Playback errors
- Stop/pause/resume/volume errors
- Cleanup errors

All errors are logged via `verbose_logger` which supports:
- Console output with rich formatting
- File logging when `-v` flag is used

### 2. Enhanced Error Logging in Hybrid Player (CLI)
**File:** `ytm_cli/hybrid_player.py`

Added logging for:
- Player initialization (MPV vs pygame selection)
- Fallback attempts when MPV is unavailable
- Playback start/stop operations
- Player availability checks

### 3. Comprehensive Test Suite
**File:** `tests/test_hybrid_player.py`

Created 18 test cases covering:

#### Initialization Tests (3)
- `test_init_prefers_mpv_when_available` - Verifies MPV is preferred
- `test_init_falls_back_to_pygame_when_mpv_unavailable` - Verifies pygame fallback
- `test_init_no_player_available` - Verifies graceful failure

#### Playback Tests (10)
- `test_is_available_pygame` - Player availability check
- `test_is_available_no_player` - No player available handling
- `test_play_with_pygame_fallback` - Play method delegation
- `test_play_failed_with_pygame_fallback` - Play failure handling
- `test_play_no_player_available` - Play when no player
- `test_stop_pygame` - Stop method delegation
- `test_pause_pygame` - Pause method delegation
- `test_resume_pygame` - Resume method delegation
- `test_is_playing_pygame` - Playing status check
- `test_cleanup_pygame` - Resource cleanup

#### Info Tests (2)
- `test_get_player_info_pygame_available` - Player info with pygame
- `test_get_player_info_no_player` - Player info with no player

#### Integration Tests (3)
- `test_pygame_player_initialization` - Pygame initialization
- `test_pygame_player_init_failure` - Pygame init failure
- `test_pygame_player_stop` - Pygame stop method

## Running Tests

### Run Hybrid Player Tests
```bash
# Run all pygame fallback tests
pytest tests/test_hybrid_player.py -v

# Run specific test class
pytest tests/test_hybrid_player.py::TestCLIHybridPlayerInitialization -v

# Run single test
pytest tests/test_hybrid_player.py::TestCLIHybridPlayerPlayback::test_play_with_pygame_fallback -v
```

### Run Simple CLI Test
```bash
# Quick verification that pygame fallback works
python3 test_pygame_cli_simple.py

# Check generated log file
cat pygame_cli_test.log
```

## Test Results

All 18 tests pass:
```
======================== 18 passed in 0.16s =========================
```

### Expected Output When Running CLI Test

When running `test_pygame_cli_simple.py`:

```
======================================================================
CLI Hybrid Player - Pygame Fallback Test
======================================================================

[Test] Initialize CLIHybridPlayerService
----------------------------------------------------------------------

────────────────────────────────────────────────────────────
🎵 Player Initialization
────────────────────────────────────────────────────────────
18:23:32   ℹ MPV not found, attempting pygame fallback...
18:23:32   ℹ Pygame mixer initialized successfully
18:23:32   ℹ Pygame player initialized successfully
✓ Using pygame for playback (fallback mode)

[Test] Verify player methods are available
----------------------------------------------------------------------
✓ Player is available
  ✓ Method 'play' exists
  ✓ Method 'pause' exists
  ✓ Method 'resume' exists
  ✓ Method 'stop' exists
  ✓ Method 'is_playing' exists
  ✓ Method 'cleanup' exists

======================================================================
Result: Using Pygame fallback (MPV not available)
======================================================================
```

## Logging in Production

When using YTM CLI with verbose logging enabled:

```bash
ytm search "song name" -v
# or
ytm play "song name" --verbose
```

The verbose log will include:
- Player initialization info (which player selected)
- Playback start/stop events
- Error messages with full exception details
- Stream extraction status
- Volume changes

## Error Handling Examples

### Example 1: Pygame Mixer Init Failure
```
[ERROR] Failed to initialize pygame mixer: ALSA lib error
[ERROR] No audio player available (mpv and pygame both unavailable)
Result: No player available
```

### Example 2: Stream URL Extraction Failure
```
[INFO] Pygame Playback
[INFO] Title: Song Name
[ERROR] Error extracting stream URL: Connection timeout
[ERROR] Failed to get audio stream URL
```

### Example 3: Successful Pygame Playback
```
[SECTION] 🎵 Pygame Playback
[INFO] Title: Song Name
[INFO] Stream URL extracted successfully
[INFO] Stream loaded into pygame mixer
[INFO] Playback finished successfully
```

## Code Quality

- All code passes ruff linting
- Proper exception chaining with `raise ... from e`
- Verbose logging integrated with existing logger
- Both console and file logging supported
- No breaking changes to existing APIs

## Verification Steps

1. ✓ Code compiles without errors
2. ✓ All 18 tests pass
3. ✓ Ruff linting passes
4. ✓ Simple CLI test runs successfully
5. ✓ Log file generation verified
6. ✓ Both console and file output working

## Future Improvements

- Add audio device enumeration logging
- Log stream bitrate/format information
- Add playback position tracking to logs
- Performance profiling for initialization
- Network diagnostics for stream failures
