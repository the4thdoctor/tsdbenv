#!/bin/bash
# tsdbenv installer - Quick setup for PostgreSQL + TimescaleDB environment manager
# Usage: curl https://raw.githubusercontent.com/wagnerbianchijr/tsdbenv/main/install.sh | bash

set -e

REPO_URL="https://github.com/wagnerbianchijr/tsdbenv.git"
INSTALL_DIR="${HOME}/.local/share/tsdbenv"

echo "🚀 Installing tsdbenv..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Install Python from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed."
    exit 1
fi

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Clone or update repository
if [ -d "$INSTALL_DIR/repo" ]; then
    echo "📦 Updating tsdbenv..."
    cd "$INSTALL_DIR/repo"
    git pull origin main
else
    echo "📦 Cloning tsdbenv repository..."
    git clone "$REPO_URL" "$INSTALL_DIR/repo"
    cd "$INSTALL_DIR/repo"
fi

# Create virtual environment
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
fi

# Activate virtual environment
source "$INSTALL_DIR/venv/bin/activate"

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install -e . > /dev/null 2>&1

# Create symlink in /usr/local/bin
LINK_PATH="/usr/local/bin/tsdbenv"
echo "🔗 Creating command symlink..."
sudo tee "$LINK_PATH" > /dev/null <<'WRAPPER'
#!/bin/bash
source "$HOME/.local/share/tsdbenv/venv/bin/activate"
python -m tsdbenv.cli "$@"
WRAPPER
sudo chmod +x "$LINK_PATH"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Quick start:"
echo "  tsdbenv new --postgres 14 --timescaledb 2.10.0 --bind-ip 127.0.0.1"
echo ""
echo "For help:"
echo "  tsdbenv --help"
