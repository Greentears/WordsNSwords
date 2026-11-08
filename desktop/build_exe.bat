@echo off
rem Builds Flashcards.exe (run this once on Windows). Result: dist\Flashcards\
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || py -m venv .venv || goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name Flashcards main.py || goto :fail

if not exist dist\Flashcards\assets mkdir dist\Flashcards\assets
copy /Y assets\hero.png dist\Flashcards\assets\hero.png >nul
echo.
echo Done. Run dist\Flashcards\Flashcards.exe. Keep it inside the WordsNSwords folder (it finds the users\ folder above it).
pause
exit /b 0

:fail
echo Build failed.
pause
exit /b 1
