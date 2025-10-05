# Troubleshooting Guide

This guide helps diagnose and fix common issues with YTM CLI.

## Table of Contents

- [Songs Skipping Continuously](#songs-skipping-continuously)
- [MPV Not Found](#mpv-not-found)
- [Authentication Issues](#authentication-issues)
- [Terminal/Curses Errors](#terminalcurses-errors)
- [Using Verbose Logging](#using-verbose-logging)

---

## Songs Skipping Continuously

### Symptoms
- Songs skip immediately without playing
- Music player keeps jumping to next song
- No audio output

### Diagnosis

Enable verbose logging to see what's happening:

```bash
python -m ytm_cli search "test song" --select 1 --verbose --log-file debug.log
```

Check the log file for MPV exit codes:
```bash
cat debug.log | grep "exited with code"
```

### Common Exit Codes

#### Exit Code 2 - Format/Extraction Error
**Cause:** Outdated yt-dlp version

**Solution:**
```bash
# Check yt-dlp version
yt-dlp --version

# Update via Homebrew (macOS/Linux)
brew upgrade yt-dlp

# Update via pip (if not using system package)
pip install --upgrade yt-dlp

# Verify update
yt-dlp --version  # Should be 2025.09.26 or newer
```

#### Exit Code 0 followed by immediate skip
**Cause:** Video not available or region-locked

**Solution:**
- Try different songs
- Check if YouTube Music is available in your region
- Verify internet connection

#### Exit Code -9 or -15
**Cause:** Process was killed (usually intentional)

**Solution:** This is normal when you quit the player

### Quick Fix Checklist

1. ✅ Update yt-dlp: `brew upgrade yt-dlp` or `pip install --upgrade yt-dlp`
2. ✅ Verify MPV is installed: `mpv --version`
3. ✅ Test MPV directly: `mpv --no-video "https://music.youtube.com/watch?v=VIDEO_ID"`
4. ✅ Check verbose logs for specific errors
5. ✅ Ensure stable internet connection

---

## MPV Not Found

### Symptoms
```
command not found: mpv
```

### Solution

**macOS (Homebrew):**
```bash
brew install mpv
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mpv
```

**Arch Linux:**
```bash
sudo pacman -S mpv
```

**Verify installation:**
```bash
mpv --version
```

---

## Authentication Issues

### OAuth Verification Error

**Symptoms:**
```
YTM CLI has not completed the Google verification process
```

**Solution 1: Add Test Users (Recommended)**
1. Go to https://console.cloud.google.com/apis/credentials/consent
2. Click 'EDIT APP'
3. Go to 'Test users' section
4. Click '+ ADD USERS'
5. Add your Gmail address
6. Try OAuth setup again

**Solution 2: Use Browser Authentication**
```bash
python -m ytm_cli auth setup-browser
```

### Full Authentication Help
```bash
# Show troubleshooting guide
python -m ytm_cli auth troubleshoot

# Check current status
python -m ytm_cli auth status

# Start fresh with browser auth
python -m ytm_cli auth setup-browser
```

---

## Terminal/Curses Errors

### Symptoms
```
Terminal error: nocbreak() returned ERR
curses.error: cbreak() returned ERR
```

### Causes
- Terminal too small
- Running in non-interactive environment (scripts, cron)
- Terminal emulator compatibility issues

### Solutions

**1. Resize Terminal**
- Ensure terminal is at least 80x24 characters
- Make window larger and try again

**2. Use Non-Interactive Mode**
```bash
# Bypass curses UI entirely
python -m ytm_cli search "song name" --select 1
```

**3. Different Terminal Emulator**
- Try iTerm2, Alacritty, or default Terminal app
- Ensure TERM environment variable is set: `echo $TERM`

---

## Using Verbose Logging

Verbose logging is your best friend for debugging. It shows exactly what's happening under the hood.

### Enable Verbose Mode

**Terminal output only:**
```bash
python -m ytm_cli search "song" --select 1 --verbose
```

**Save to file for analysis:**
```bash
python -m ytm_cli search "song" --select 1 --verbose --log-file debug.log
```

**Short form:**
```bash
python -m ytm_cli search "song" -s 1 -v --log-file debug.log
```

### What Verbose Logging Shows

- ✅ API queries and response counts
- ✅ Disliked song filtering statistics
- ✅ Radio playlist generation details
- ✅ MPV process lifecycle (PID, start, exit)
- ✅ Exit codes and error messages
- ✅ URLs being played
- ✅ IPC socket paths
- ✅ Timestamps for all operations

### Analyzing Log Files

**Check for errors:**
```bash
grep -i error debug.log
```

**See all exit codes:**
```bash
grep "exited with code" debug.log
```

**View MPV errors:**
```bash
grep -A 5 "MPV error" debug.log
```

**See what songs were attempted:**
```bash
grep "Now playing" debug.log
```

---

## Still Having Issues?

If these solutions don't help:

1. **Create a verbose log:**
   ```bash
   python -m ytm_cli search "test" -s 1 -v --log-file issue.log
   ```

2. **Gather system info:**
   ```bash
   echo "OS: $(uname -a)" > system_info.txt
   echo "Python: $(python --version)" >> system_info.txt
   echo "MPV: $(mpv --version | head -1)" >> system_info.txt
   echo "yt-dlp: $(yt-dlp --version)" >> system_info.txt
   ```

3. **Report the issue:**
   - Include both `issue.log` and `system_info.txt`
   - Describe what you expected vs what happened
   - Share the exact command you ran

---

## Quick Reference

### Diagnosis Commands

```bash
# Check versions
mpv --version
yt-dlp --version
python --version

# Test MPV directly
mpv --no-video "https://music.youtube.com/watch?v=dQw4w9WgXcQ"

# Enable verbose logging
python -m ytm_cli search "test" -s 1 -v --log-file debug.log

# Check auth status
python -m ytm_cli auth status
```

### Update Commands

```bash
# Update yt-dlp (Homebrew)
brew upgrade yt-dlp

# Update yt-dlp (pip)
pip install --upgrade yt-dlp

# Update Python dependencies
pip install --upgrade -r requirements.txt
```

### Reset/Fresh Start

```bash
# Disable authentication
python -m ytm_cli auth disable

# Clear dislikes (if needed)
rm dislikes.json

# Clear playlists (if needed)
rm -rf playlists/

# Fresh auth setup
python -m ytm_cli auth setup-browser
```
