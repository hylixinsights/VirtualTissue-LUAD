@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the project environment first. See README.md.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8026 in your browser.
".venv\Scripts\python.exe" server.py --port 8026
pause
