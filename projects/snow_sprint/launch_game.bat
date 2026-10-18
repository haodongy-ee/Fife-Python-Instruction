@echo off
setlocal
cd /d "%~dp0"
python ski_game.py
if errorlevel 1 (
  echo.
  echo Activate your Python 3.11 environment and install requirements first.
  pause
)
endlocal
