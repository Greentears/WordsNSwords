@echo off
rem Double-click to start the flashcards (sets everything up on first run).
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating virtual environment...
    python -m venv .venv || py -m venv .venv || goto :nopython
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)

start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:nopython
echo Python was not found. Install Python 3.10+ from python.org and tick "Add python.exe to PATH".
pause
exit /b 1

:fail
echo Installing the dependencies failed.
pause
exit /b 1
