# Codebase Structure

## Directory Structure
```
ytm/
├── ytm_cli/                 # Main package directory
│   ├── __init__.py         # Package version (__version__ = "0.4.0")
│   ├── __main__.py         # Package entry point
│   ├── main.py             # CLI interface and command routing
│   ├── player.py           # MPV integration and playback controls  
│   ├── ui.py               # Curses-based terminal interfaces
│   ├── auth.py             # Authentication (OAuth/browser)
│   ├── playlists.py        # Local playlist management
│   ├── dislikes.py         # Song dislike and filtering
│   ├── config.py           # Configuration management
│   └── utils.py            # Utility functions
├── auth/                   # Authentication credential storage
├── planning/               # Development planning documents
├── .github/workflows/      # CI configuration (pylint.yml)
├── ytm-cli.py             # Legacy entry point (backward compatibility)
├── requirements.txt        # Python dependencies
├── config.ini             # Application configuration
├── CLAUDE.md              # Development guidelines for Claude
├── README.md              # User documentation
├── CHANGELOG.md           # Version history
├── .bumpversion.cfg       # Version management configuration
└── .gitignore             # Git ignore rules
```

## Key Files Purpose
- **ytm_cli/main.py**: Central CLI command routing, argparse setup, all subcommands
- **ytm_cli/player.py**: MPV integration via IPC socket, playback controls
- **ytm_cli/ui.py**: All curses-based UI components, selection interfaces
- **ytm_cli/auth.py**: AuthManager class for OAuth and browser authentication
- **ytm_cli/playlists.py**: PlaylistManager for local JSON-based playlists
- **ytm_cli/dislikes.py**: DislikeManager for song filtering system
- **ytm_cli/config.py**: Configuration loading and global instances

## Data Storage
- **Playlists**: `playlists/` directory (JSON files, gitignored)
- **Dislikes**: `dislikes.json` (gitignored for privacy)
- **Auth tokens**: `auth/` directory (OAuth/browser credentials)
- **Configuration**: `config.ini` (user preferences)

## Entry Points
1. **Modern**: `python -m ytm_cli` (via __main__.py → main.py)
2. **Legacy**: `python ytm-cli.py` (direct script execution)
3. **Both support**: Direct search args and interactive mode