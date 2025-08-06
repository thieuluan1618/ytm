# YTM CLI Test Plan

## Overview

This test plan outlines the comprehensive testing strategy for the YouTube Music CLI application, covering unit tests, integration tests, end-to-end tests, and manual testing procedures.

## Test Environment Setup

### Prerequisites

- Python 3.8+ installed
- MPV media player installed and accessible via PATH
- Virtual environment with all dependencies installed
- Test data fixtures (mock songs, playlists, etc.)
- Network connectivity for YouTube Music API

### Test Data

- Mock YouTube Music API responses
- Sample playlist files
- Test audio streams
- Invalid/corrupted data files for error testing

## Test Categories

### 1. Unit Tests

#### 1.1 Authentication Module (auth.py)

- **Test OAuth Setup**

  - ✓ Valid client credentials
  - ✓ Invalid client credentials
  - ✓ Missing credentials
  - ✓ Credential file scanning
  - ✓ OAuth token refresh
  - ✓ Token expiration handling

- **Test Browser Authentication**

  - ✓ Valid headers parsing
  - ✓ Invalid headers format
  - ✓ Clipboard integration
  - ✓ File-based header input
  - ✓ cURL command parsing

- **Test Authentication Status**
  - ✓ Auth enabled/disabled states
  - ✓ Method detection (OAuth vs Browser)
  - ✓ File existence checks

#### 1.2 Configuration Module (config.py)

- **Test Config Loading**

  - ✓ Default values
  - ✓ Custom config values
  - ✓ Invalid config entries
  - ✓ Missing config file

- **Test Settings**
  - ✓ Songs to display count
  - ✓ MPV flags parsing
  - ✓ Playlist directory configuration

#### 1.3 Playlist Manager (playlists.py)

- **Test Playlist Creation**

  - ✓ Valid playlist name
  - ✓ Special characters in name
  - ✓ Duplicate playlist names
  - ✓ Empty playlist name
  - ✓ Unicode playlist names

- **Test Song Management**

  - ✓ Add song to playlist
  - ✓ Add duplicate song
  - ✓ Remove song by index
  - ✓ Remove song by video ID
  - ✓ Invalid song data

- **Test Playlist Operations**
  - ✓ List all playlists
  - ✓ Get specific playlist
  - ✓ Delete playlist
  - ✓ Non-existent playlist handling

#### 1.4 Dislike Manager (dislikes.py)

- **Test Dislike Operations**

  - ✓ Dislike new song
  - ✓ Dislike already disliked song
  - ✓ Remove dislike
  - ✓ Clear all dislikes

- **Test Filtering**
  - ✓ Filter search results
  - ✓ Filter radio playlist
  - ✓ Filter local playlist
  - ✓ Empty results after filtering

#### 1.5 Lyrics Service (lyrics_service.py)

- **Test Lyrics Fetching**

  - ✓ Successful lyrics fetch
  - ✓ No lyrics available
  - ✓ Network timeout
  - ✓ Invalid video ID

- **Test LRC Parsing**
  - ✓ Valid LRC format
  - ✓ Invalid timestamps
  - ✓ Empty lyrics
  - ✓ Malformed LRC data

#### 1.6 Player Module (player.py)

- **Test MPV Communication**

  - ✓ Send valid commands
  - ✓ Get playback position
  - ✓ Get pause state
  - ✓ Socket connection errors
  - ✓ MPV process crashes

- **Test Playback Controls**
  - ✓ Play/pause toggle
  - ✓ Next/previous track
  - ✓ Add to playlist during playback
  - ✓ Dislike handling (two-step system)

#### 1.7 UI Module (ui.py)

- **Test Selection UI**

  - ✓ Navigation (j/k, arrow keys)
  - ✓ Song selection
  - ✓ Boundary conditions (first/last item)
  - ✓ Terminal resize handling

- **Test Lyrics Display**
  - ✓ Synchronized scrolling
  - ✓ No lyrics available
  - ✓ Escape to return

### 2. Integration Tests

#### 2.1 Search and Play Flow

- **Test Complete Search Flow**
  - ✓ Search query → Results → Selection → Playback
  - ✓ Empty search results
  - ✓ Network errors during search
  - ✓ Radio playlist generation

#### 2.2 Playlist Workflow

- **Test Playlist Integration**
  - ✓ Create playlist → Add songs → Play playlist
  - ✓ Dislike filtering in playlist playback
  - ✓ Add song during search
  - ✓ Add song during playback

#### 2.3 Authentication Flow

- **Test Auth Setup and Usage**
  - ✓ OAuth setup → Authenticated search
  - ✓ Browser auth → Personalized results
  - ✓ Disable auth → Guest mode

### 3. End-to-End Tests

#### 3.1 User Scenarios

- **New User Flow**

  ```
  1. Install and run first time
  2. Search for a song
  3. Play with radio
  4. Create first playlist
  5. Add songs to playlist
  ```

- **Power User Flow**

  ```
  1. Setup OAuth authentication
  2. Search with personalized results
  3. Manage multiple playlists
  4. Use keyboard shortcuts efficiently
  5. Dislike songs to refine results
  ```

- **Playlist Management Flow**
  ```
  1. Create multiple playlists
  2. Add songs from different sources
  3. Play playlists
  4. Delete unwanted playlists
  5. Handle playlist conflicts
  ```

### 4. Performance Tests

#### 4.1 Response Time

- Search query response < 2 seconds
- UI navigation response < 50ms
- Playlist loading < 100ms
- MPV command response < 100ms

#### 4.2 Resource Usage

- Memory usage < 100MB during playback
- CPU usage < 10% during idle
- No memory leaks over extended usage

### 5. Compatibility Tests

#### 5.1 Platform Testing

- **Operating Systems**

  - ✓ macOS (10.15+)
  - ✓ Ubuntu Linux (20.04+)
  - ✓ Windows 10/11
  - ✓ Arch Linux

- **Python Versions**

  - ✓ Python 3.8
  - ✓ Python 3.9
  - ✓ Python 3.10
  - ✓ Python 3.11
  - ✓ Python 3.12

- **Terminal Emulators**
  - ✓ iTerm2
  - ✓ Terminal.app
  - ✓ GNOME Terminal
  - ✓ Windows Terminal
  - ✓ Alacritty

### 6. Edge Cases and Error Handling

#### 6.1 Network Issues

- ✓ No internet connection
- ✓ Slow connection (timeout handling)
- ✓ API rate limiting
- ✓ Partial response data

#### 6.2 File System Issues

- ✓ Read-only file system
- ✓ Disk full scenarios
- ✓ Permission denied
- ✓ Corrupted data files

#### 6.3 User Input Validation

- ✓ Empty search queries
- ✓ Special characters in input
- ✓ Very long input strings
- ✓ Unicode input handling

#### 6.4 Concurrent Operations

- ✓ Multiple terminal instances
- ✓ Playlist modification during playback
- ✓ Configuration changes during runtime

### 7. Security Tests

#### 7.1 Authentication Security

- ✓ OAuth token storage security
- ✓ Browser headers privacy
- ✓ No credential leakage in logs

#### 7.2 Input Sanitization

- ✓ Command injection prevention
- ✓ Path traversal prevention
- ✓ Safe file naming

### 8. Accessibility Tests

#### 8.1 Keyboard Navigation

- ✓ All features accessible via keyboard
- ✓ Consistent shortcut keys
- ✓ No mouse dependency

#### 8.2 Terminal Compatibility

- ✓ Works with screen readers
- ✓ High contrast mode support
- ✓ Minimal terminal size requirements

### 9. Regression Tests

#### 9.1 Feature Regression

- ✓ Basic search functionality
- ✓ Playback controls
- ✓ Playlist operations
- ✓ Authentication methods

#### 9.2 Bug Fix Verification

- ✓ MPV UI sync issue
- ✓ Two-step dislike system
- ✓ Auto-playlist selection

## Test Execution Plan

### Phase 1: Unit Tests (Week 1)

- Run all unit tests with pytest
- Achieve 90%+ code coverage
- Fix any failing tests

### Phase 2: Integration Tests (Week 2)

- Test component interactions
- Verify data flow between modules
- Test error propagation

### Phase 3: E2E & Manual Tests (Week 3)

- Execute user scenarios
- Platform compatibility testing
- Performance benchmarking

### Phase 4: Bug Fixes & Retesting (Week 4)

- Address discovered issues
- Regression testing
- Final acceptance testing

## Test Automation

### CI/CD Pipeline

```yaml
- Unit Tests: Run on every commit
- Integration Tests: Run on pull requests
- E2E Tests: Run on main branch
- Performance Tests: Weekly scheduled runs
```

### Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ytm_cli --cov-report=html

# Run specific test category
pytest tests/test_playlists.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest -m integration

# Run performance tests
pytest -m performance --benchmark
```

## Success Criteria

### Coverage Requirements

- Unit test coverage: ≥ 90%
- Integration test coverage: ≥ 80%
- Critical path coverage: 100%

### Quality Metrics

- Zero critical bugs
- < 5 minor bugs
- All user scenarios pass
- Performance benchmarks met

## Risk Mitigation

### High Risk Areas

1. **YouTube API Changes**: Mock data for testing, version pinning
2. **MPV Compatibility**: Test multiple MPV versions
3. **Terminal Compatibility**: Test various terminal emulators
4. **Network Reliability**: Implement retry logic and timeouts

### Contingency Plans

- Fallback to mock data if API unavailable
- Alternative audio players if MPV fails
- Graceful degradation for terminal features

## Test Documentation

### Test Reports

- Daily test execution summary
- Bug tracking and status
- Coverage reports
- Performance benchmarks

### Test Maintenance

- Update tests for new features
- Refactor tests for clarity
- Maintain test data fixtures
- Document test dependencies

## Manual Test Checklist

### Pre-release Checklist

- [ ] Fresh install on clean system
- [ ] All authentication methods work
- [ ] Search returns relevant results
- [ ] Playback controls responsive
- [ ] Playlists persist correctly
- [ ] Dislikes filter properly
- [ ] Lyrics display correctly
- [ ] Help documentation accurate
- [ ] Error messages helpful
- [ ] Graceful shutdown

This test plan should be reviewed and updated regularly as the application evolves and new features are added.
