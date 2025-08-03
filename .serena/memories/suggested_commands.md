# Suggested Commands

## Development Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Update requirements after adding dependencies
pip freeze > requirements.txt
```

## Running the Application
```bash
# Interactive mode (search prompt)
python -m ytm_cli

# Direct search from command line
python -m ytm_cli "song name or artist"

# Legacy entry point (backward compatibility)
python ytm-cli.py "song name"
```

## Authentication Commands
```bash
python -m ytm_cli auth setup-oauth      # OAuth setup (recommended)
python -m ytm_cli auth setup-browser    # Browser headers setup
python -m ytm_cli auth status           # Check auth status
python -m ytm_cli auth scan             # Scan for credential files
python -m ytm_cli auth troubleshoot     # OAuth troubleshooting
python -m ytm_cli auth disable          # Disable authentication
```

## Playlist Management
```bash
python -m ytm_cli playlist list         # List all playlists
python -m ytm_cli playlist create       # Create new playlist
python -m ytm_cli playlist show <name>  # View playlist contents
python -m ytm_cli playlist play <name>  # Play entire playlist
python -m ytm_cli playlist delete <name> # Delete playlist
```

## System Utilities (macOS/Darwin)
```bash
# Standard Unix commands available
git status
git add .
git commit -m "message"
ls -la
find . -name "*.py"
grep -r "pattern" .
```

## Version Management
```bash
# Using bump2version (configured in .bumpversion.cfg)
bump2version patch   # 0.4.0 -> 0.4.1
bump2version minor   # 0.4.0 -> 0.5.0
bump2version major   # 0.4.0 -> 1.0.0
```

## System Dependencies
```bash
# Ensure mpv is installed for audio playback
brew install mpv  # macOS
```