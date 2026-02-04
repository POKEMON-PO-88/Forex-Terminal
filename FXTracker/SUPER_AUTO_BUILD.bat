@echo off
REM ============================================================================
REM SUPER AUTO BUILD - DOWNLOADS EVERYTHING AUTOMATICALLY
REM No Python? No problem! This downloads and installs it for you!
REM ============================================================================

color 0B
cls
title FX Tracker - Super Auto Build

echo.
echo ========================================================================
echo   FX TRADE TRACKER - SUPER AUTO BUILD
echo   Downloads Python automatically if needed!
echo ========================================================================
echo.
echo This script will:
echo   ✅ Check if Python is installed
echo   ✅ Download Python if needed (auto-install)
echo   ✅ Install all packages automatically
echo   ✅ Build your .exe
echo   ✅ Everything automatic!
echo.
echo Just sit back and relax...
echo This takes 5-10 minutes if Python needs to be downloaded.
echo.
pause

cls

REM ============================================================================
REM STEP 1: Check if Python Already Installed
REM ============================================================================

echo.
echo [1/7] Checking for Python...
echo ========================================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Python NOT found - will download automatically
    goto INSTALL_PYTHON
) else (
    python --version
    echo Python already installed - skipping download
    goto PYTHON_READY
)

REM ============================================================================
REM AUTO-INSTALL PYTHON
REM ============================================================================

:INSTALL_PYTHON
echo.
echo [2/7] Downloading Python...
echo ========================================================================
echo Please wait... this may take 2-5 minutes depending on internet speed
echo.

REM Create temp directory
if not exist "%TEMP%\FXTracker" mkdir "%TEMP%\FXTracker"
cd /d "%TEMP%\FXTracker"

REM Download Python installer using PowerShell
echo Downloading Python 3.11 installer...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe' -OutFile 'python_installer.exe'}"

if not exist "python_installer.exe" (
    echo.
    echo ERROR: Failed to download Python installer
    echo.
    echo Please check your internet connection
    echo Or manually install Python from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo ✅ Python installer downloaded
echo.

REM Install Python silently
echo [3/7] Installing Python...
echo ========================================================================
echo Installing Python silently...
echo This takes 1-2 minutes...
echo.

REM Silent install with PATH added automatically
python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1

REM Wait for installation to complete
timeout /t 60 /nobreak >nul

echo ✅ Python installed
echo.

REM Go back to original directory
cd /d "%~dp0"

REM Refresh PATH in current session
call refreshenv >nul 2>&1

REM Verify Python works
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  Python installed but not in PATH yet
    echo Please close this window and run again
    echo OR restart your computer
    echo.
    pause
    exit /b 1
)

goto PYTHON_READY

REM ============================================================================
REM PYTHON IS READY - Continue with Build
REM ============================================================================

:PYTHON_READY
echo.
echo [4/7] Python is ready!
echo ========================================================================
python --version
echo.
pause

REM ============================================================================
REM STEP 2: Check for fx_tracker_team.py
REM ============================================================================

echo.
echo [5/7] Checking for fx_tracker_team.py...
echo ========================================================================
if not exist fx_tracker_team.py (
    echo.
    echo ERROR: fx_tracker_team.py not found!
    echo.
    echo Make sure this file is in the same folder as this .bat file
    echo Current folder: %CD%
    echo.
    pause
    exit /b 1
)

echo ✅ Script found
echo.
pause

REM ============================================================================
REM STEP 3: Install PyInstaller
REM ============================================================================

echo.
echo [6/7] Installing build tools...
echo ========================================================================
echo Installing PyInstaller and dependencies...
echo This takes 1-2 minutes...
echo.

pip install --upgrade pip --quiet --disable-pip-version-check
pip install pyinstaller flask flask-socketio --quiet --disable-pip-version-check

if errorlevel 1 (
    echo WARNING: Some packages may have failed
    echo Continuing anyway...
)

echo ✅ Build tools ready
echo.
pause

REM ============================================================================
REM STEP 4: Clean old builds
REM ============================================================================

echo.
echo Cleaning old builds...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "*.spec" del /q "*.spec" 2>nul
echo ✅ Cleaned
echo.

REM ============================================================================
REM STEP 5: Build the .exe
REM ============================================================================

echo.
echo [7/7] Building FX Trade Tracker.exe...
echo ========================================================================
echo Building... this takes 2-3 minutes
echo Please wait...
echo.

REM Check for icon
if exist fx_icon.ico (
    set ICON_PARAM=--icon=fx_icon.ico
    echo Using custom icon: fx_icon.ico
) else (
    set ICON_PARAM=
    echo Using default Windows icon (no fx_icon.ico found)
)
echo.

REM Build the .exe
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "FX Trade Tracker" ^
    %ICON_PARAM% ^
    --add-data "fx_tracker_team.py;." ^
    --hidden-import=flask ^
    --hidden-import=flask_socketio ^
    --hidden-import=sqlite3 ^
    --hidden-import=werkzeug ^
    --hidden-import=jinja2 ^
    --hidden-import=engineio ^
    --hidden-import=socketio ^
    --noconfirm ^
    fx_tracker_team.py

REM ============================================================================
REM Check Success
REM ============================================================================

if not exist "dist\FX Trade Tracker.exe" (
    echo.
    echo ========================================================================
    echo   BUILD FAILED!
    echo ========================================================================
    echo.
    echo Check error messages above
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM SUCCESS!
REM ============================================================================

cls
color 0A
echo.
echo ========================================================================
echo   🎉 SUCCESS! YOUR APP IS READY! 🎉
echo ========================================================================
echo.
echo Location: %CD%\dist\FX Trade Tracker.exe
echo.

dir "dist\FX Trade Tracker.exe" | find "FX Trade Tracker.exe"

echo.
echo ========================================================================
echo   WHAT YOU HAVE:
echo ========================================================================
echo.
echo ✅ ONE .exe file
echo ✅ Everything bundled inside (including Python!)
echo ✅ Users DON'T need Python
echo ✅ Just double-click to run
echo ✅ Works on any Windows 10+ PC
echo.
echo ========================================================================
echo   TEST IT NOW:
echo ========================================================================
echo.
choice /C YN /M "Test the .exe now (Y/N)"

if errorlevel 2 goto SKIP_TEST
if errorlevel 1 goto RUN_TEST

:RUN_TEST
echo.
echo Starting FX Trade Tracker...
echo Browser will open in a few seconds...
echo.
start "" "%CD%\dist\FX Trade Tracker.exe"
timeout /t 5 >nul
echo.
echo ✅ If dashboard opened in browser - IT WORKS!
echo.
goto END

:SKIP_TEST
echo.
echo Skipped test
echo.

:END
echo ========================================================================
echo   DISTRIBUTE TO TEAM:
echo ========================================================================
echo.
echo 1. Go to: dist\FX Trade Tracker.exe
echo 2. Send this ONE file to your team
echo 3. They double-click it
echo 4. Dashboard opens
echo 5. Done!
echo.
echo ========================================================================
echo   IMPORTANT:
echo ========================================================================
echo.
echo ⚠️  This .exe ONLY works on Windows
echo.
echo For Mac users:
echo   - They should access via browser
echo   - One Windows PC runs the .exe
echo   - Mac users go to: http://that-pc:8080
echo.
echo ========================================================================
echo.
pause

REM Open dist folder
explorer dist

echo.
echo Build complete!
echo.