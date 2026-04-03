#!/bin/sh
# install.sh — installer for pip-select
# Usage: curl -fsSL https://raw.githubusercontent.com/rsnemmen/pip-select/main/install.sh | sh

set -e

REPO="https://raw.githubusercontent.com/rsnemmen/pip-select/main"
SCRIPT="pip-select.py"
BIN_NAME="pip-select"

# Determine install directory
USER_BIN="$HOME/.local/bin"
SYSTEM_BIN="/usr/local/bin"

_in_path() {
    case ":$PATH:" in
        *":$1:"*) return 0 ;;
        *) return 1 ;;
    esac
}

if _in_path "$USER_BIN" || [ -d "$USER_BIN" ]; then
    INSTALL_DIR="$USER_BIN"
    USE_SUDO=""
else
    INSTALL_DIR="$SYSTEM_BIN"
    USE_SUDO="sudo"
fi

echo "Installing pip-select to $INSTALL_DIR ..."

# Create dir if needed
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
fi

# Download the script
DEST="$INSTALL_DIR/$SCRIPT"
if command -v curl >/dev/null 2>&1; then
    $USE_SUDO curl -fsSL "$REPO/$SCRIPT" -o "$DEST"
elif command -v wget >/dev/null 2>&1; then
    $USE_SUDO wget -qO "$DEST" "$REPO/$SCRIPT"
else
    echo "Error: curl or wget is required." >&2
    exit 1
fi

$USE_SUDO chmod +x "$DEST"

# Create a pip-select symlink (no .py extension)
LINK="$INSTALL_DIR/$BIN_NAME"
if [ "$LINK" != "$DEST" ]; then
    $USE_SUDO ln -sf "$DEST" "$LINK"
fi

echo "Installed: $DEST"
echo "Symlink:   $LINK"

# Warn if install dir is not in PATH
if ! _in_path "$INSTALL_DIR"; then
    echo ""
    echo "Warning: $INSTALL_DIR is not in your PATH."
    echo "Add this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
    echo ""
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
    echo "Then restart your shell or run: source ~/.bashrc"
fi

echo ""
echo "Done. Run 'pip-select --help' to get started."
