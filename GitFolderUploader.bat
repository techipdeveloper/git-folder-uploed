@echo off
echo ============================================
echo   Git Folder Uploader - Techip
echo ============================================
echo.

:: Check if the compiled .exe exists
if exist "%~dp0dist\GitFolderUploader.exe" (
    echo Launching Git Folder Uploader...
    start "" "%~dp0dist\GitFolderUploader.exe"
    exit /b 0
)

:: Fall back to running via Python
echo [INFO] Compiled .exe not found. Launching via Python...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install Python from https://www.python.org/downloads/
    echo Or run build.bat to create the .exe first.
    pause
    exit /b 1
)

:: Install Pillow if needed
pip show Pillow >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required package: Pillow...
    pip install Pillow
)

echo.
echo Starting application...
python "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
