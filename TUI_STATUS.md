# TUI Development Status

## Current Layout Structure

```
┌─────────────────────────────────────────┐
│ Now Playing (60%) │  Queue (40%)        │
│ 🎵 Now Playing    │ 📻 Queue            │
│ Song info...      │ 1. Song A           │
│ Controls...       │ 2. Song B           │
├─────────────────────────────────────────┤
│ 🔍 [Search input field..................]│
│ [🔍 Search] [🤖 Ay AI]                  │
│ Search Results Table                    │
├─────────────────────────────────────────┤
│ Footer (Keyboard Shortcuts)             │
└─────────────────────────────────────────┘
```

### Completed Features

✅ **Layout Structure**
- Removed Header and Playlist Sidebar (hidden for now)
- Split screen: Now Playing (60%) + Queue (40%)
- Search section at bottom with 2 rows:
  - Row 1: Full-width search input
  - Row 2: Buttons (🔍 Search, 🤖 Ay AI)
- Footer with keyboard shortcuts

✅ **Search Functionality**
- Search input works
- Results display in DataTable
- LLM-enhanced search button integrated
- Song selection triggers playback

✅ **Widget Implementation**
- `NowPlayingWidget` - Fully implemented with:
  - Song title, artist, album display
  - Progress bar and time display
  - Playback controls (⏮ ⏯ ⏭ 🔀 🔁)
  - Action buttons (❤️ 👎 📝 📜)
  - Reactive properties for all fields

- `QueueWidget` - Fully implemented with:
  - Dynamic queue list display
  - Color coding (current=green, played=dimmed, upcoming=cyan)
  - Scrollable list view

## Current Problem: Empty Widgets

### Symptom
- Notifications show updates are happening correctly:
  - "✓ Updated Now Playing"
  - "✓ Updated Queue (X songs)"
  - "NowPlaying.update_song: [title] by [artist]"
- **BUT** the widgets remain visually empty/unchanged

### What We've Tried

1. **Added `on_mount()` methods**
   - Initialized default display values
   - Manually updated labels on mount

2. **Added `refresh()` calls**
   - Called after updating reactive properties
   - Called after queue list updates

3. **Added initial content to Labels**
   - Changed from empty strings `""` to "No song playing", "---"

4. **Added extensive error handling**
   - Try/catch in all watchers
   - Error notifications (none are triggered)

5. **Updated reactive properties correctly**
   - `self.song_title = title`
   - `self.artist_name = artist`
   - `self.album_name = album`

### Files Involved

**Widgets:**
- `ytm_cli/tui/widgets/now_playing.py` - Now Playing widget
- `ytm_cli/tui/widgets/queue.py` - Queue widget
- `ytm_cli/tui/widgets/search.py` - Search interface

**Main App:**
- `ytm_cli/tui/app.py` - Main TUI application
- `ytm_cli/tui/styles.tcss` - CSS styling

**Core Logic:**
- `ytm_cli/tui/player_factory.py` - Hybrid player service
- `ytm_cli/tui/player_service.py` - Player service interface
- `ytm_cli/tui/pygame_player.py` - Pygame player implementation

## Next Steps to Debug

### 1. Verify Textual Reactive System

The reactive properties might not be triggering watchers. Need to check:

```python
# In NowPlayingWidget
song_title = reactive("No song playing")  # Is this correct syntax?
artist_name = reactive("---")

# Watchers should be triggered automatically
def watch_song_title(self, title: str) -> None:
    # This should be called when self.song_title changes
    pass
```

**Possible Issue:** The reactive system might need the widget to be fully mounted before property changes trigger watchers.

**Test:** Try using `self.call_after_refresh()` or `self.set_timer()` to update after the widget is fully rendered.

### 2. Check Widget Mounting Order

The widgets might not be fully mounted when we try to update them. Current flow:

```
app.py:on_song_selected()
  → generate_and_play_radio()
    → play_song()
      → now_playing.update_song()  ← Might be called too early?
      → queue.update_queue()       ← Might be called too early?
```

**Possible Fix:** Add a check to ensure widgets are mounted:

```python
if self.is_mounted:
    # Update widgets
```

### 3. Direct DOM Manipulation Alternative

Instead of using reactive properties, try direct updates:

```python
def update_song(self, song: dict):
    # Skip reactive properties, update DOM directly
    label = self.query_one("#song-title-display", Label)
    label.update(f"[bold cyan]{song['title']}[/bold cyan]")
    # ... etc
```

### 4. Check CSS Visibility

The widgets might be rendered but hidden by CSS. Check:
- `overflow: hidden` might be hiding content
- `height` constraints might be too small
- `display` properties

### 5. Textual DevTools

Use Textual's built-in debugging:

```bash
textual console
# In another terminal:
python -m ytm_cli.tui.app
```

This will show Textual's internal logs and help identify if widgets are receiving updates.

### 6. Simplify to Minimal Test Case

Create a minimal test to verify reactive properties work:

```python
from textual.app import App
from textual.reactive import reactive
from textual.widgets import Label

class TestWidget(Widget):
    test_value = reactive("Initial")

    def watch_test_value(self, value):
        self.query_one(Label).update(value)

    def compose(self):
        yield Label("Initial")

# Test if updating test_value triggers the watcher
```

## Debugging Commands

```bash
# Activate environment
source venv/bin/activate

# Run TUI
python -m ytm_cli.tui.app

# Run with Textual console (in separate terminals)
textual console
python -m ytm_cli.tui.app

# Test widget instantiation
python3 -c "
from ytm_cli.tui.widgets.now_playing import NowPlayingWidget
widget = NowPlayingWidget()
print('Widget created')
"
```

## Related Documentation

- **Textual Reactive Docs**: https://textual.textualize.io/guide/reactivity/
- **Textual Widgets Docs**: https://textual.textualize.io/guide/widgets/
- **Project Instructions**: `CLAUDE.md`
- **Layout Diagram**: See top of this document

## Quick Reference

### Key Files Modified
- `ytm_cli/tui/app.py` - Removed Header & Sidebar, updated layout
- `ytm_cli/tui/widgets/search.py` - Split into 2 rows (input + buttons)
- `ytm_cli/tui/widgets/now_playing.py` - Added on_mount, refresh, error handling
- `ytm_cli/tui/widgets/queue.py` - Added on_mount, refresh, error handling
- `ytm_cli/tui/styles.tcss` - Removed sidebar CSS, adjusted widths

### Git Status
```
M ytm_cli/tui/__init__.py
M ytm_cli/tui/app.py
M ytm_cli/tui/styles.tcss
M ytm_cli/tui/widgets/search.py
M ytm_cli/tui/widgets/now_playing.py
M ytm_cli/tui/widgets/queue.py
```

## Hypothesis

**Most Likely Issue:** The Textual reactive system requires widgets to be in a specific state before watchers are triggered. The updates might be happening before the widget DOM is fully initialized, causing the watcher methods to silently fail (despite no exceptions being thrown).

**Evidence:**
- No error messages appear
- Notifications confirm methods are being called
- Initial content shows (proves widget is rendered)
- Updates don't reflect (proves watchers aren't working)

**Recommended Fix:**
1. Check if widget `is_mounted` before updating
2. Use `self.call_after_refresh(callback)` to defer updates
3. Or bypass reactive system and update DOM directly in `update_song()`
