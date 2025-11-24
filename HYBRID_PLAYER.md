# Hybrid Player Architecture

## Overview

YTM now uses a hybrid player approach that automatically selects the best available audio backend for both TUI and CLI modes:

```
┌─────────────────────────────────┐
│   HybridPlayerService           │
│  (TUI Player Factory)           │
└──────────────┬──────────────────┘
                │
         ┌──────┴──────┐
         ▼             ▼
    ┌─────────┐   ┌──────────┐
    │   mpv   │   │ pygame   │
    │ (Primary)   │(Fallback)│
    └─────────┘   └──────────┘

┌─────────────────────────────────┐
│  CLIHybridPlayerService         │
│  (CLI Player Factory)           │
└──────────────┬──────────────────┘
                │
         ┌──────┴──────┐
         ▼             ▼
    ┌─────────┐   ┌──────────┐
    │   mpv   │   │ pygame   │
    │ (Primary)   │(Fallback)│
    └─────────┘   └──────────┘
```

## Initialization Flow

1. **Check for mpv** - Tests if `mpv` binary is available in PATH
   - **TUI**: If found → Use `TUIPlayerService` (high quality, full controls)
   - **CLI**: If found → Use `CLIHybridPlayerService` with mpv backend
   - Print: `✓ Using mpv for playback (high quality, full controls)`

2. **Fall back to pygame** - If mpv not available
   - Initialize pygame mixer
   - If successful → Use `PygamePlayerService` (shared between TUI and CLI)
   - Print: `✓ Using pygame for playback (fallback mode)`

3. **No player available** - If both fail
   - User sees error when trying to play
   - Print: `❌ No audio player available. Install mpv or pygame`

## Player Implementations

### MPV (Primary)
**TUI File:** `ytm_cli/tui/player_service.py`
**CLI File:** `ytm_cli/hybrid_player.py` (CLIHybridPlayerService)

**Features:**
- Direct YouTube Music URL streaming
- IPC socket for fine-grained control
- Seek/time position tracking
- Equalizer and effects support
- Background process

**Requirements:**
- `mpv` binary installed system-wide

### Pygame (Fallback)
**File:** `ytm_cli/tui/pygame_player.py` (shared between TUI and CLI)

**Features:**
- Pure Python audio mixer
- Thread-based playback
- Volume control
- Basic play/pause/stop

**Requirements:**
- Python package: `pygame>=2.5.2`
- No external binary dependencies

## Unified Interface

Both players implement the same API through `HybridPlayerService`:

```python
player = HybridPlayerService()  # Auto-selects best available

# Common interface
player.play(video_id, title)     # Start playback
player.pause()                    # Pause
player.resume()                   # Resume
player.stop()                     # Stop
player.is_playing()               # Check status
player.cleanup()                  # Clean up resources

# Get player info
info = player.get_player_info()
# {'type': 'mpv'|'pygame', 'available': bool, 'playing': bool}
```

## Installation

### Install pygame (optional but recommended)
```bash
pip install pygame>=2.5.2
```

### Or install mpv (recommended for best quality)
```bash
# macOS
brew install mpv

# Ubuntu/Debian
sudo apt-get install mpv

# Fedora
sudo dnf install mpv

# Arch
sudo pacman -S mpv

# Windows
# Download from https://mpv.io/installation/
```

## Usage in TUI

The app automatically detects and uses the appropriate player:

```python
class YTMApp(App):
    def __init__(self):
        self.player = HybridPlayerService()  # Auto-select
        # Now supports both mpv and pygame seamlessly
```

When playing a song, the notification shows which player is active:

```
▶ Playing: Song Title (mpv)       # Using mpv
▶ Playing: Song Title (pygame)    # Using pygame
```

## Usage in CLI Mode

The CLI mode also supports hybrid player through `CLIHybridPlayerService`:

```python
from ytm_cli.hybrid_player import CLIHybridPlayerService

player = CLIHybridPlayerService()  # Auto-selects best available

# Common interface
player.play(video_id, title)     # Start playback
player.pause()                    # Pause
player.resume()                   # Resume
player.stop()                     # Stop
player.is_playing()               # Check status
player.cleanup()                  # Clean up resources

# Get player info
info = player.get_player_info()
# {'type': 'mpv'|'pygame', 'available': bool, 'playing': bool}
```

The CLI player automatically detects available backends and provides the same fallback behavior as the TUI version.

## Migration Path

### For Users
- **Current setup (mpv only)**: Works as before, faster startup for both TUI and CLI
- **With pygame installed**: Automatic fallback support for both modes
- **Neither installed**: Get helpful error message during playback

### For Developers
- **TUI**: Use `HybridPlayerService` for new features
- **CLI**: Use `CLIHybridPlayerService` for new features
- Both backends implement the same interface
- Add new features to abstract player class first

## Advantages

✅ **Best of Both Worlds**
- mpv: High quality, professional features
- pygame: No external dependencies

✅ **Seamless Fallback**
- Auto-detects what's available
- No configuration needed
- Works in both TUI and CLI modes

✅ **Future Proof**
- Easy to add more backends
- Consistent interface across modes

✅ **User Friendly**
- Clear feedback about which player is active
- Helpful error messages
- Same experience in TUI and CLI

## Testing

```bash
# Test TUI hybrid player initialization
python -c "from ytm_cli.tui.player_factory import HybridPlayerService; \
p = HybridPlayerService(); print(p.get_player_info())"

# Test CLI hybrid player initialization
python -c "from ytm_cli.hybrid_player import CLIHybridPlayerService; \
p = CLIHybridPlayerService(); print(p.get_player_info())"

# Test with both backends
mpv --version && echo "✓ mpv available"
python -c "import pygame; print('✓ pygame available')"
```

## Troubleshooting

### No audio when playing
- Check which player is active (see notification)
- If pygame: might be blocked by firewall (requires URL streaming)
- If mpv: verify `mpv` can play YouTube Music URLs manually

### Player not switching
- Make sure pygame is installed: `pip install pygame`
- Check mpv is in PATH: `which mpv`

### Install specific backend
```bash
# Force mpv installation (system package)
brew install mpv  # macOS

# Install pygame fallback
pip install pygame==2.5.2
```
