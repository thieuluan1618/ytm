#!/bin/bash
# One-shot setup for YTM CLI on Linux/macOS
# Creates venv, installs dependencies, and configures the `ytm` alias.

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🎵 YTM CLI Setup"
echo "================"
echo ""

# 1. Check Python (>= 3.7)
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found. Please install Python 3.7+ first."
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)'; then
    FOUND=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    echo "❌ Python 3.7+ required, found $FOUND"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
echo "✅ Python $PY_VERSION detected"

# 2. Check / install mpv
if command -v mpv >/dev/null 2>&1; then
    echo "✅ mpv detected ($(mpv --version 2>/dev/null | head -n1))"
else
    echo "⚠️  mpv not found"
    OS_NAME=$(uname -s)
    INSTALL_CMD=""
    NEEDS_SUDO=0

    if [ "$OS_NAME" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            INSTALL_CMD="brew install mpv"
        else
            echo "   Homebrew not found. Install it from https://brew.sh then rerun this script."
        fi
    elif [ "$OS_NAME" = "Linux" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            INSTALL_CMD="sudo apt-get update && sudo apt-get install -y mpv"; NEEDS_SUDO=1
        elif command -v dnf >/dev/null 2>&1; then
            INSTALL_CMD="sudo dnf install -y mpv"; NEEDS_SUDO=1
        elif command -v pacman >/dev/null 2>&1; then
            INSTALL_CMD="sudo pacman -S --noconfirm mpv"; NEEDS_SUDO=1
        elif command -v zypper >/dev/null 2>&1; then
            INSTALL_CMD="sudo zypper install -y mpv"; NEEDS_SUDO=1
        else
            echo "   No supported package manager detected. See https://mpv.io/installation/"
        fi
    fi

    if [ -n "$INSTALL_CMD" ]; then
        echo "   Proposed install command: $INSTALL_CMD"
        [ $NEEDS_SUDO -eq 1 ] && echo "   (this will prompt for your sudo password)"
        read -p "   Install mpv now? (y/n) " -n 1 -r; echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            eval "$INSTALL_CMD"
            if command -v mpv >/dev/null 2>&1; then
                echo "✅ mpv installed"
            else
                echo "❌ mpv install failed. Please install manually and rerun."
                exit 1
            fi
        else
            echo "   Skipping mpv install — ytm playback will not work until it's installed."
        fi
    fi
fi
echo ""

# 3. Create venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    if ! python3 -m venv venv; then
        echo "❌ Failed to create virtual environment"
        echo "   On Debian/Ubuntu you may need: sudo apt install python3-venv"
        exit 1
    fi
else
    echo "📦 Virtual environment already exists"
fi

# 4. Install dependencies
echo "📥 Installing dependencies..."
# shellcheck disable=SC1091
if ! source venv/bin/activate; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

if ! pip install --quiet --upgrade pip; then
    echo "❌ Failed to upgrade pip"
    exit 1
fi

if ! pip install --quiet -r requirements.txt; then
    echo "❌ Failed to install dependencies from requirements.txt"
    exit 1
fi
echo "✅ Dependencies installed"
echo ""

# 5. Configure shell alias
echo "🔗 Configuring 'ytm' alias..."
if ! bash "$SCRIPT_DIR/setup_alias.sh"; then
    echo "❌ Alias setup failed. You can run setup_alias.sh manually later."
    exit 1
fi

echo ""
echo "🎉 Setup complete! Reload your shell and run:  ytm"
