# YTM - YouTube Music CLI

A simple, interactive command-line tool for YouTube Music. Core philosophy: **Keep it simple for the listener to enjoy music.**

## Core Commands

**Setup:**

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

**Run:**

```bash
python -m ytm_cli                    # Interactive mode
python -m ytm_cli "song name"        # Direct search
ytm "song name"                      # If alias setup
```

**Testing & Quality:**

```bash
pytest                               # Run test suite
pytest --cov=ytm_cli                 # With coverage
pytest tests/test_specific.py        # Single file
ruff check .                         # Lint
black .                              # Format
make test                            # Run all checks
```

**Setup Alias (Optional):**

```bash
./setup_alias.sh                     # Linux/macOS
.\setup_alias.ps1                    # Windows PowerShell
setup_alias.bat                      # Windows Command Prompt
```

## Project Structure

```
ytm/
├── ytm_cli/              # Main application code
│   ├── __init__.py       # Version definition (0.5.0)
│   ├── main.py           # Entry point, search & play logic
│   ├── player.py         # MPV playback control
│   ├── ui.py             # Curses-based terminal UI
│   ├── playlists.py      # Local playlist management
│   ├── dislikes.py       # Song dislike system
│   ├── lyrics_service.py # Lyrics fetching
│   ├── auth.py           # Authentication (in development, DO NOT USE)
│   └── config.py         # Configuration management
├── tests/                # Test suite (pytest)
├── setup_alias.*         # Cross-platform alias setup scripts
├── config.ini            # User configuration
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata & build config
└── CHANGELOG.md          # Version history
```

## Development Patterns

**Code Style:**

- Python 3.8+ compatibility
- Type hints encouraged
- 100-char line limit (ruff)
- No complex abstractions - keep it simple
- Test-first for bug fixes

**Key Technologies:**

- `ytmusicapi` - YouTube Music API
- `mpv` - Media player (must be installed system-wide)
- `rich` - Terminal formatting
- `curses` - Terminal UI (preferred over rich for interactive UIs)

**UI Philosophy:**

- Single-key shortcuts during playback (space, n, b, l, a, d, q)
- Vim-like navigation (j/k keys)
- Non-disruptive - actions don't interrupt playback
- Immediate visual feedback

## Git Workflow

**Commit Message Format (Conventional Commits):**

```
<type>[optional scope]: <description>

```

**Types:**

- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance, dependencies
- `docs:` - Documentation only
- `refactor:` - Code restructuring
- `test:` - Test additions/modifications
- `style:` - Code formatting

**Branches:**

- `main` - Stable releases (default branch)
- `develop` - Active development
- Feature branches: `feature/<name>` or `bugfix/<name>`

**Before Committing:**

```bash
pytest                    # All tests pass
ruff check .              # No lint errors
git diff --cached         # Review ALL changes for secrets/credentials
```

## Version Management

**Current Version:** 0.5.0

**Version Locations (must stay in sync):**

- `ytm_cli/__init__.py` - `__version__ = "0.5.0"`
- `pyproject.toml` - `version = "0.5.0"`

**Bump Version:**

```bash
# Edit both files above, then update CHANGELOG.md
# Add entry under ## [X.Y.Z] - YYYY-MM-DD
git commit -m "chore: bump version X.Y.Z → A.B.C"
```

## Dependencies

**Management:**

- Automated via Dependabot (weekly Monday checks)
- Manual updates: `pip install --upgrade <package> && pip freeze > requirements.txt`
- Critical: `yt-dlp` version affects playback (currently 2025.10.22)

**Key Dependencies:**

- `yt-dlp==2025.10.22` - YouTube downloader (fixes skipping songs)
- `ytmusicapi==1.10.3` - YouTube Music API client
- `rich==14.0.0` - Terminal formatting
- `mpv==1.0.8` - Python MPV bindings

## Configuration

**User Config:** `config.ini`

```ini
[general]
songs_to_display = 10

[mpv]
flags = --no-video

[playlists]
directory = playlists
```

## Features & Constraints

**Working Features:**

- ✅ Search and play music
- ✅ Interactive terminal UI
- ✅ Local playlist management
- ✅ Song dislike system (two-step from playlists)
- ✅ Lyrics display
- ✅ Radio mode (auto-generated playlists)

**In Development (DO NOT EXPOSE):**

- ⚠️ Authentication system (`auth.py`) - not functional, excluded from docs

**File Privacy:**

- `dislikes.json` - in `.gitignore`
- `playlists/` - in `.gitignore`
- `auth/` - in `.gitignore`

## Common Tasks

**Add New Feature:**

1. Write failing test in `tests/test_<module>.py`
2. Implement in appropriate `ytm_cli/<module>.py`
3. Update CHANGELOG.md under `## [Unreleased]`
4. Update README.md if user-facing
5. Run `pytest && ruff check .`

**Fix Bug:**

1. Add test reproducing bug
2. Fix in source
3. Verify test passes
4. Update CHANGELOG.md if notable

**Update Documentation:**

- User docs → `README.md`
- Developer docs → `CLAUDE.md`
- AI agent context → `AGENTS.md` (this file)
- Version history → `CHANGELOG.md`

## External Requirements

**System Dependencies:**

- `mpv` media player (install via `brew install mpv` or system package manager)
- `yt-dlp` (installed via pip, but system version may also be used)

**Testing MPV:**

```bash
mpv --version                        # Verify installation
mpv --no-video "https://music.youtube.com/watch?v=VIDEO_ID"  # Test playback
```

## Troubleshooting

**Songs skipping continuously:**

- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check version: `yt-dlp --version` (should be 2025.09.26 or newer)

**Verbose logging:**

```bash
python -m ytm_cli search "test" -s 1 -v --log-file debug.log
```

**Common Issues:**

- MPV not found → Install system-wide
- Curses errors → Terminal too small or non-interactive environment
- Import errors → Activate venv first

## Evidence Required for PR

**Every PR must include:**

- ✅ All tests passing (`pytest`)
- ✅ No lint errors (`ruff check .`)
- ✅ CHANGELOG.md updated (if user-facing change)
- ✅ No secrets in diff (`git diff --cached`)
- ✅ Version numbers synced (if version bump)
- ✅ Conventional commit message format

## Quick Reference

**Start working:**

```bash
cd ~/Repos/ytm
source venv/bin/activate
```

**Run checks:**

```bash
make test                 # or: pytest && ruff check .
```

**Commit:**

```bash
git add <files>
git commit -m "feat: description"
```
