#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting JobHunt setup..."

# 1. Detect Python version
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Error: Python is not installed. Please install Python and try again."
    exit 1
fi

echo "Using $PYTHON_BIN..."

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_BIN -m venv venv || { echo "❌ Failed to create virtual environment"; exit 1; }
else
    echo "✅ Virtual environment already exists."
fi

# 3. Detect OS and Activate venv
echo "🔧 Activating virtual environment..."
case "$(uname -s)" in
    CYGWIN*|MINGW32*|MSYS*|MINGW*)
        # Windows (Git Bash, MSYS, etc.)
        source venv/Scripts/activate || { echo "❌ Failed to activate venv on Windows"; exit 1; }
        ;;
    *)
        # Mac / Linux
        source venv/bin/activate || { echo "❌ Failed to activate venv"; exit 1; }
        ;;
esac

# 4. Install requirements
echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt || { echo "❌ Failed to install requirements"; exit 1; }

# 5. Playwright browser installation
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium || { echo "❌ Failed to install playwright browser"; exit 1; }

echo ""
echo "✨ Setup complete. Copy .env.example to .env and fill in your keys."
echo "   Command: cp .env.example .env"
