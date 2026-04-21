#!/bin/bash
# Move to the directory where this script is located (important for double-click execution)
cd "$(dirname "$0")"

# Configuration
VENV_DIR="venv"

echo "🚀 Starting Gemini TTS Assistant for macOS..."

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate venv
source $VENV_DIR/bin/activate

# Install requirements
echo "📥 Checking dependencies..."
pip install -r requirements.txt --quiet

# Check for .env
if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found! Please make sure to add your GEMINI_API_KEY."
fi

# Run server
echo "🌐 Server starting at http://localhost:8000"
python3 main.py
