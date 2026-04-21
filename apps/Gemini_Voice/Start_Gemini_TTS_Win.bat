@echo off
set VENV_DIR=venv

echo 🚀 Starting Gemini TTS Assistant for Windows...

:: Check if venv exists
if not exist %VENV_DIR% (
    echo 📦 Creating virtual environment...
    python -m venv %VENV_DIR%
)

:: Activate venv
call %VENV_DIR%\Scripts\activate

:: Install requirements
echo 📥 Checking dependencies...
pip install -r requirements.txt --quiet

:: Check for .env
if not exist .env (
    echo ⚠️  WARNING: .env file not found! Please make sure to add your GEMINI_API_KEY.
)

:: Run server
echo 🌐 Server starting at http://localhost:8000
python main.py

pause
