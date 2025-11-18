# 🚀 Quick Start - Textual TUI

## ✅ Fixed! Ready to Use

The Textual TUI is now ready. Here's how to use it:

## 1. Reload Your Shell

```bash
# Reload .zshrc to get the fixed alias
source ~/.zshrc

# Or restart your terminal
```

## 2. Launch the TUI

```bash
# New way (works now!)
ytm tui

# Alternative: Full command
cd ~/Repos/ytm
source venv/bin/activate
python -m ytm_cli tui
```

## 3. What Was Fixed

### Issue 1: Wrong venv path
**Before:** `~/Repos/.venv/bin/activate` ❌  
**After:** `~/Repos/ytm/venv/bin/activate` ✅

### Issue 2: Old script path
**Before:** `python ytm-cli.py` ❌  
**After:** `python -m ytm_cli` ✅

### Issue 3: CSS errors
**Before:** `bar-color`, `bar-complete-color` ❌  
**After:** `color: $accent` ✅

## 4. Using the TUI

Once launched, you'll see:
- **Left Sidebar**: Your playlists
- **Top**: Search bar with LLM button
- **Middle**: Search results table
- **Bottom Left**: Now playing with controls
- **Bottom Right**: Queue

### Keyboard Shortcuts
- `q` - Quit
- `/` - Focus search
- `p` - Play/Pause
- `n` - Next
- `b` - Previous
- `l` - Lyrics
- `a` - Add to playlist
- `d` - Dislike

## 5. Known Limitations (Phase 1)

The UI is complete but backend integration is pending:
- ⚠️ Search shows mock data (not real YouTube Music yet)
- ⚠️ Playback controls are placeholders
- ⚠️ Playlists show examples (not your actual playlists)

**These will be connected in Phase 2!**

## 6. Test Import

To verify installation:
```bash
cd ~/Repos/ytm
source venv/bin/activate
python -c "from ytm_cli.tui import YTMApp; print('✅ TUI ready!')"
```

## 7. If You Get Errors

### "ModuleNotFoundError: No module named 'textual'"
```bash
cd ~/Repos/ytm
source venv/bin/activate
pip install textual==6.6.0
```

### "ytm: command not found"
```bash
source ~/.zshrc
# Or restart terminal
```

### CSS parsing errors
Already fixed! Just pull latest code.

## 8. Development Mode

To develop the TUI with live reload:
```bash
cd ~/Repos/ytm
source venv/bin/activate

# Terminal 1: Run console for debugging
textual console

# Terminal 2: Run with dev mode
textual run --dev ytm_cli/tui/app.py
```

## 9. Next Steps

1. ✅ Launch TUI: `ytm tui`
2. ✅ Explore the interface
3. 🚧 Wait for Phase 2 (backend integration)
4. 🎵 Enjoy full music playback!

## 10. Alias Reference

Your new alias does:
```bash
cd ~/Repos/ytm/          # Go to project
source venv/bin/activate  # Activate venv
python -m ytm_cli         # Run CLI with all args
```

So `ytm tui` becomes:
```bash
cd ~/Repos/ytm/ && source venv/bin/activate && python -m ytm_cli tui
```

---

**Status**: ✅ **Ready to Launch!**

Try it now:
```bash
source ~/.zshrc  # Reload
ytm tui          # Launch!
```

🎉 **Enjoy your new modern terminal music player UI!**
