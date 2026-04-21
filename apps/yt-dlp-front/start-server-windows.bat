@echo off
cd %~dp0
echo Starting Web-DLP Server...
cd app
..\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
if %errorlevel% neq 0 (
    echo.
    echo Error occurred during startup. Make sure dependencies are installed.
    pause
)
