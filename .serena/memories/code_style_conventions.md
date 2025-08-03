# Code Style and Conventions

## Code Style
- **Python version compatibility**: 3.8+ to 3.13.5
- **Docstrings**: Triple-quoted strings for function/class documentation
- **String formatting**: Uses f-strings and format strings
- **Method naming**: Snake_case for functions and methods
- **Class naming**: PascalCase for classes (e.g., `AuthManager`, `PlaylistManager`)
- **Private methods**: Use underscore prefix (e.g., `_setup_browser_from_clipboard`)
- **Module-level constants**: UPPER_CASE (e.g., `CLIPBOARD_AVAILABLE`)

## File Organization
- **Package structure**: Modular with `__init__.py` and `__main__.py`
- **Entry points**: Both `python -m ytm_cli` and legacy `ytm-cli.py` supported
- **Version management**: Centralized in `ytm_cli/__init__.py` as `__version__`

## Import Style
- Standard library imports first
- Third-party imports second
- Local imports last
- Conditional imports used for optional features

## UI Conventions
- **Primary UI**: curses for all interactive interfaces
- **Secondary formatting**: rich for simple text formatting
- **Navigation**: Vim-like keys (j/k) consistently used
- **Keyboard shortcuts**: Single letters during playback (space, n, b, l, a, d, q)

## Error Handling
- Graceful fallbacks for optional features
- Clear user feedback for authentication issues
- Non-disruptive error handling during playback

## Configuration
- INI format for configuration files
- JSON for data storage (playlists, dislikes)
- Platform-safe file naming and UTF-8 encoding