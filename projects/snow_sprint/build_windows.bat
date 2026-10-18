@echo off
setlocal
cd /d "%~dp0"
python -m pip install pyinstaller
if errorlevel 1 goto failure
python -m PyInstaller --noconfirm --onedir --windowed --name SnowSprint ski_game.py
if errorlevel 1 goto failure
echo.
echo Build complete. Zip the ENTIRE dist\SnowSprint folder for students.
pause
exit /b 0
:failure
echo Build failed. Activate the working fife environment and try again.
pause
exit /b 1
