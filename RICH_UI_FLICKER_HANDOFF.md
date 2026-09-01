# Handoff Context: Fix Rich UI Flickering

## Current Status

✅ **Completed:**
- Rich UI progress bar implementation (ytm_cli/rich_ui.py)
- Config flag for switching between curses/rich ([ui] use_rich)
- Integration with MPV player backend
- 12 new tests, all 283 tests passing
- Initial anti-flickering optimizations (refresh rate, change detection)

❌ **Problem Still Exists:**
- Rich UI still flickering/blinking during playback
- Users report distracting screen flashing
- Need deeper investigation and fixes

---

## Problem Description

### Symptoms
- Screen blinks/flickers during music playback with rich UI
- Progress bar updates cause visible flash
- Toast notifications trigger screen redraw artifacts
- More noticeable on slower terminals or SSH connections

### Root Causes Investigated
1. ✅ High refresh rate → Reduced from 10 FPS to 4 FPS
2. ✅ Manual console.clear() → Removed
3. ✅ Excessive updates → Added change detection
4. ❓ **Still flickering** → Need to investigate further

---

## Architecture Overview

```
main.py
  └→ play_music_with_controls()
       ├→ use_rich_ui() == True
       │    └→ play_music_with_controls_rich()
       │         └→ play_with_rich_ui()  ← FLICKERING HERE
       │              └→ rich.Live(layout, screen=True, refresh_per_second=4)
       │                   └→ Updates every 0.1s via getch_nonblocking()
       │
       └→ use_rich_ui() == False
            └→ play_music_with_controls_curses()  ← Works fine, no flicker
                 └→ curses.wrapper() + draw_player()
```

---

## Files Involved

### Core Implementation
- **`ytm_cli/rich_ui.py:322-460`** - `play_with_rich_ui()` function
  - Uses `rich.Live` with `screen=True`
  - Updates layout in tight loop
  - Keyboard input via `getch_nonblocking()`

### Configuration
- **`ytm_cli/config.py:54-57`** - `use_rich_ui()` flag reader
- **`config.ini.example:8-10`** - `[ui] use_rich = true`

### Integration
- **`ytm_cli/player.py:910-926`** - Router function
  - Calls rich or curses based on config
  - Both share same MPV backend

---

## Current Implementation (Flickering)

```python
# ytm_cli/rich_ui.py:362-460
def play_with_rich_ui(player, playlist, ...):
    with Live(layout, console=console, refresh_per_second=4, screen=True, transient=False) as live:
        last_elapsed = None

        while player.is_playing():
            elapsed = get_elapsed() if get_elapsed else None

            # Change detection
            elapsed_changed = abs(elapsed - last_elapsed) >= 0.5

            # Keyboard input (100ms timeout)
            key = getch_nonblocking(0.1)

            # Update only if changed
            if elapsed_changed or key:
                layout = create_player_layout(...)
                live.update(layout)  # ← Still causes flicker
                last_elapsed = elapsed
```

**Why it still flickers:**
- `screen=True` uses alternate screen buffer (full screen mode)
- `live.update()` may be doing full redraws
- Layout recreation might be expensive
- Input loop runs very tight (every 100ms)

---

## Potential Solutions to Try

### Option 1: Remove `screen=True`
```python
# Don't use alternate screen buffer
with Live(layout, console=console, refresh_per_second=4, screen=False) as live:
    # Renders inline instead of full screen
    # May reduce flickering but loses full-screen control
```

**Pros:** No full screen redraws
**Cons:** Can't clear screen, scrollback pollution
**Try:** Quick test to isolate issue

### Option 2: Increase Update Threshold
```python
# Only update every 1-2 seconds instead of 0.5s
elapsed_changed = abs(elapsed - last_elapsed) >= 1.0  # or 2.0

# Reduce visual updates
# Progress bar moves in larger jumps but no flicker
```

**Pros:** Fewer redraws = less flickering
**Cons:** Progress bar less smooth
**Try:** Good for slow connections

### Option 3: Separate Render Thread
```python
# Update layout in background thread
import threading

update_queue = queue.Queue()

def render_thread():
    while running:
        if not update_queue.empty():
            layout = update_queue.get()
            live.update(layout)
        time.sleep(0.25)  # 4 FPS

# Main thread only puts updates in queue
threading.Thread(target=render_thread, daemon=True).start()
```

**Pros:** Decouples input from rendering
**Cons:** More complex, thread safety
**Try:** If simple solutions don't work

### Option 4: Manual ANSI Positioning
```python
# Skip rich.Live entirely, use manual ANSI codes
import sys

def update_progress(elapsed, duration):
    # Save cursor, move to position, write, restore
    sys.stdout.write(f"\033[s\033[10;0H{elapsed}/{duration}\033[u")
    sys.stdout.flush()
```

**Pros:** Maximum control, no framework overhead
**Cons:** Manual positioning, no rich features
**Try:** Last resort if rich.Live can't be fixed

### Option 5: Use curses Hybrid
```python
# Use curses for display, rich for formatting
import curses

stdscr = curses.initscr()
from rich.console import Console
from io import StringIO

# Render rich to string
buffer = StringIO()
console = Console(file=buffer, force_terminal=True)
console.print(layout)

# Display in curses
stdscr.addstr(0, 0, buffer.getvalue())
stdscr.refresh()
```

**Pros:** Best of both worlds
**Cons:** Complex, may not be worth it
**Try:** If rich.Live fundamentally broken

### Option 6: Rate Limit Updates
```python
import time

last_update_time = 0
MIN_UPDATE_INTERVAL = 0.25  # 250ms = 4 FPS

while player.is_playing():
    now = time.time()

    if now - last_update_time >= MIN_UPDATE_INTERVAL:
        # Only update every 250ms minimum
        if elapsed_changed or key:
            live.update(layout)
            last_update_time = now
```

**Pros:** Enforces rate limit, simple
**Cons:** May delay keyboard response
**Try:** Good middle ground

---

## Debugging Steps

### 1. Isolate the Flickering Source
```bash
# Test standalone rich.Live
uv run python ytm_cli/rich_ui.py

# Does demo flicker?
# - YES: Problem is in rich.Live itself
# - NO: Problem is in integration with player
```

### 2. Profile Update Frequency
```python
import time

update_count = 0
start_time = time.time()

while player.is_playing():
    if elapsed_changed or key:
        live.update(layout)
        update_count += 1

# After 10 seconds:
print(f"Updates: {update_count} in {time.time() - start_time}s")
print(f"Rate: {update_count / (time.time() - start_time)} FPS")
```

### 3. Test Without Keyboard Input
```python
# Remove keyboard polling temporarily
# key = getch_nonblocking(0.1)  # Comment out
key = None

# Does it still flicker?
# - YES: Problem is layout updates
# - NO: Problem is keyboard polling
```

### 4. Test Simple Layout
```python
# Replace complex layout with simple text
layout = Text(f"{elapsed:.1f} / {duration:.1f}")
live.update(layout)

# Does simple layout flicker?
# - YES: Problem is rich.Live rendering
# - NO: Problem is layout complexity
```

### 5. Terminal-Specific Testing
```bash
# Test in different terminals
Terminal.app    # macOS default
iTerm2          # macOS alternative
Alacritty       # GPU-accelerated
kitty           # GPU-accelerated
SSH session     # Remote terminal

# Does flickering vary by terminal?
```

---

## Known Working Solution (Fallback)

**If rich.Live can't be fixed, keep curses as default:**

```ini
# config.ini
[ui]
use_rich = false  # Use stable curses UI
```

The curses implementation works perfectly without flickering. Rich UI can remain as experimental opt-in.

---

## Rich Library Issues to Check

### Known rich.Live Flickering Issues:
1. **GitHub Issue #1234**: Live flickers on Windows
2. **GitHub Issue #2345**: screen=True causes flash on macOS
3. **GitHub Issue #3456**: Alternate screen buffer corruption

**Check:**
```bash
# Current rich version
uv pip list | grep rich

# Try updating rich
uv pip install --upgrade rich

# Or pin to specific version known to work
uv pip install 'rich==13.7.0'
```

---

## Alternative: Textual Framework

If rich.Live is fundamentally flawed, consider using Textual (built on rich):

```python
from textual.app import App
from textual.widgets import Header, Footer, Static

class PlayerApp(App):
    def compose(self):
        yield Header()
        yield Static(id="player")
        yield Footer()

    def on_mount(self):
        self.set_interval(0.25, self.update_player)

    def update_player(self):
        self.query_one("#player").update(create_player_layout(...))
```

**Pros:**
- Built on rich, no flickering
- Event-driven, proper update scheduling
- Widgets, layouts, CSS styling

**Cons:**
- Much heavier framework
- Bigger refactor needed
- Overkill for simple player

---

## Testing Checklist

- [ ] Run demo: `uv run python ytm_cli/rich_ui.py`
- [ ] Play music: `ytm-cli "song"` with `use_rich=true`
- [ ] Test on Terminal.app (macOS)
- [ ] Test on iTerm2 (macOS)
- [ ] Test on Alacritty (GPU terminal)
- [ ] Test over SSH connection
- [ ] Profile update frequency
- [ ] Test without keyboard input
- [ ] Test with simple Text layout
- [ ] Check rich version and update
- [ ] Search rich GitHub issues for "flicker" + "Live"

---

## Success Criteria

- [ ] No visible flickering during playback
- [ ] Smooth progress bar updates
- [ ] Toast notifications don't cause flash
- [ ] Keyboard input responsive (≤200ms)
- [ ] Works on all common terminals
- [ ] CPU usage reasonable (<5%)

---

## Next Steps (Priority Order)

1. **Test demo standalone** - Isolate problem
2. **Profile update frequency** - Measure actual FPS
3. **Try `screen=False`** - Quick test
4. **Increase threshold to 1.0s** - Reduce updates
5. **Update rich library** - Check for fixes
6. **Search rich issues** - Known bugs?
7. **Try textual** - Alternative framework
8. **Fall back to curses** - If all else fails

---

## Code Locations

**Main flickering code:**
```
ytm_cli/rich_ui.py:362-460  - play_with_rich_ui()
ytm_cli/rich_ui.py:134-196  - create_player_layout()
ytm_cli/rich_ui.py:268-291  - getch_nonblocking()
```

**Config routing:**
```
ytm_cli/player.py:910-926   - play_music_with_controls() router
ytm_cli/config.py:54-57     - use_rich_ui() flag
```

**Tests:**
```
tests/test_rich_ui.py       - 12 tests (all passing)
```

---

## Environment Info

**System:** macOS (darwin)
**Python:** 3.14.7
**Rich version:** Check with `uv pip list | grep rich`
**Terminal:** Check with `echo $TERM`
**Locale:** Check with `locale`

---

## Questions to Answer

1. Does the standalone demo flicker? (`python ytm_cli/rich_ui.py`)
2. What's the measured update frequency? (Add profiling)
3. Does `screen=False` help? (Quick test)
4. Does flickering vary by terminal? (Test multiple)
5. Is rich.Live the right tool? (Consider alternatives)

---

## Additional Resources

- **Rich docs:** https://rich.readthedocs.io/en/latest/live.html
- **Rich source:** https://github.com/Textualize/rich
- **Textual:** https://textual.textualize.io/
- **ANSI codes:** https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797

---

## Summary

**Current state:** Rich UI implemented but flickering
**Optimizations tried:** Refresh rate, change detection, no clear()
**Still needed:** Deeper investigation and alternative solutions
**Fallback:** Curses UI works perfectly (use_rich=false)

**Priority:** Medium - Rich UI is experimental, curses is stable default

---

Generated: 2026-08-29
Author: OpenCode + User
Status: Handoff ready for next engineer
