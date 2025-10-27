#!/bin/bash
# Setup script to create 'ytm' command alias for Linux/macOS
# Supports: zsh, bash, fish shells

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/venv"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at: $VENV_PATH"
    echo ""
    echo "Please run:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Detect shell and config file
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

echo "🔍 Detected shell: $SHELL_NAME"
echo ""

if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
    ALIAS_LINE="alias ytm='cd $SCRIPT_DIR && source $VENV_PATH/bin/activate && python -m ytm_cli'"
    echo "Found: ~/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
    ALIAS_LINE="alias ytm='cd $SCRIPT_DIR && source $VENV_PATH/bin/activate && python -m ytm_cli'"
    echo "Found: ~/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_RC="$HOME/.bash_profile"
    ALIAS_LINE="alias ytm='cd $SCRIPT_DIR && source $VENV_PATH/bin/activate && python -m ytm_cli'"
    echo "Found: ~/.bash_profile"
elif [ -f "$HOME/.config/fish/config.fish" ]; then
    SHELL_RC="$HOME/.config/fish/config.fish"
    ALIAS_LINE="alias ytm='cd $SCRIPT_DIR; and source $VENV_PATH/bin/activate.fish; and python -m ytm_cli'"
    echo "Found: ~/.config/fish/config.fish"
else
    echo "❌ Could not find shell configuration file"
    echo ""
    echo "Supported shells:"
    echo "  - zsh    (~/.zshrc)"
    echo "  - bash   (~/.bashrc or ~/.bash_profile)"
    echo "  - fish   (~/.config/fish/config.fish)"
    echo ""
    echo "Please create one of these files or add this alias manually:"
    echo "  alias ytm='cd $SCRIPT_DIR && source $VENV_PATH/bin/activate && python -m ytm_cli'"
    exit 1
fi

# Check if alias already exists
if grep -q "alias ytm=" "$SHELL_RC"; then
    echo "✅ 'ytm' alias already exists in $SHELL_RC"
    echo ""
    echo "Current alias:"
    grep "alias ytm=" "$SHELL_RC"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping update."
        exit 0
    fi
    # Remove old alias
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/alias ytm=/d' "$SHELL_RC"
    else
        sed -i '/alias ytm=/d' "$SHELL_RC"
    fi
fi

# Add the alias
echo "" >> "$SHELL_RC"
echo "# YTM CLI - YouTube Music CLI Tool" >> "$SHELL_RC"
echo "$ALIAS_LINE" >> "$SHELL_RC"

echo "✅ Successfully added 'ytm' alias to $SHELL_RC"
echo ""
echo "To use immediately, run:"
echo "  source $SHELL_RC"
echo ""
echo "Or simply restart your terminal."
echo ""
echo "Then use: ytm [search query]"
