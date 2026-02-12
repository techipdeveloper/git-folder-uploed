@echo off
echo ============================================
echo   GitLab Folder Pusher - Build Script
echo   Developed by Techip Developers
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/3] Building executable...
pyinstaller --onefile --windowed --name "GitLabFolderPusher" --add-data "logo.png;." --icon "logo.png" main.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo Your .exe is located at:
echo   dist\GitLabFolderPusher.exe
echo.
echo You can copy GitLabFolderPusher.exe and logo.png to any folder and run it.
echo.
pause
