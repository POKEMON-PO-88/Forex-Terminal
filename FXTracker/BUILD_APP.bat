@echo off
REM ============================================================================
REM FX TRADE TRACKER - BUILD TOOL
REM Creates standalone .exe from Python code
REM ============================================================================

color 0B
cls
title Building FX Trade Tracker

echo.
echo ========================================================================
echo   FX TRADE TRACKER - BUILD TOOL
echo   Creates ONE .exe file that users can double-click
echo ========================================================================
echo.
echo This will create: FX Trade Tracker.exe
echo   - Standalone (no Python needed by users)
echo   - Custom icon (if you have fx_icon.ico)
echo   - Everything bundled inside
echo.
echo Press any key to start building...
pause >nul

cls

REM ============================================================================
REM STEP 1: Check Python
REM ============================================================================

echo.
echo [1/6] Checking Python...
echo ========================================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo You need Python to BUILD the .exe
    echo (Users won't need Python to RUN it)
    echo.
    echo Download from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

python --version
echo OK - Python found
echo.
pause

REM ============================================================================
REM STEP 2: Check if Python script exists
REM ============================================================================

echo.
echo [2/6] Checking for fx_tracker_team.py...
echo ========================================================================
if not exist fx_tracker_team.py (
    echo.
    echo ERROR: fx_tracker_team.py not found!
    echo.
    echo Make sure these files are in the same folder:
    echo   - fx_tracker_team.py
    echo   - BUILD_APP.bat (this file)
    echo.
    echo Current folder: %CD%
    echo.
    pause
    exit /b 1
)

echo OK - Script found
echo.
pause

REM ============================================================================
REM STEP 3: Install PyInstaller
REM ============================================================================

echo.
echo [3/6] Installing PyInstaller...
echo ========================================================================
echo This tool bundles Python + your code into ONE .exe
echo Installing... (takes 30-60 seconds)
echo.

pip install pyinstaller --quiet --disable-pip-version-check
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    echo Try running as Administrator
    pause
    exit /b 1
)

echo OK - PyInstaller ready
echo.
pause

REM ============================================================================
REM STEP 4: Install app dependencies
REM ============================================================================

echo.
echo [4/6] Installing app dependencies...
echo ========================================================================
echo These will be bundled into the .exe
echo Installing... (takes 30-60 seconds)
echo.

pip install flask flask-socketio --quiet --disable-pip-version-check
if errorlevel 1 (
    echo WARNING: Some packages failed, continuing anyway...
)

echo OK - Dependencies ready
echo.
pause

REM ============================================================================
REM STEP 5: Check for icon
REM ============================================================================

echo.
echo [5/6] Checking for icon...
echo ========================================================================

if exist fx_icon.ico (
    echo OK - Found fx_icon.ico, will use custom icon
    set ICON_PARAM=--icon=fx_icon.ico
) else (
    echo No fx_icon.ico found - will use default Windows icon
    echo (Optional: Create fx_icon.ico for custom icon)
    set ICON_PARAM=
)

echo.
pause

REM ============================================================================
REM STEP 6: Clean old builds
REM ============================================================================

echo.
echo Cleaning old builds...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "*.spec" del /q "*.spec" 2>nul
echo OK - Cleaned
echo.

REM ============================================================================
REM STEP 7: Build the .exe
REM ============================================================================

echo.
echo [6/6] Building FX Trade Tracker.exe...
echo ========================================================================
echo This takes 2-3 minutes...
echo Please wait...
echo.

REM Build command - using %ICON_PARAM% which is set above
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
REM Check if build succeeded
REM ============================================================================

if not exist "dist\FX Trade Tracker.exe" (
    echo.
    echo ========================================================================
    echo   BUILD FAILED!
    echo ========================================================================
    echo.
    echo Check error messages above
    echo.
    echo Common issues:
    echo   - Missing packages: pip install flask flask-socketio
    echo   - Antivirus blocking: Add folder to exclusions
    echo   - Permissions: Run as Administrator
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
echo   SUCCESS! YOUR APP IS READY!
echo ========================================================================
echo.
echo Location: %CD%\dist\FX Trade Tracker.exe
echo.

REM Show file info
dir "dist\FX Trade Tracker.exe" | find "FX Trade Tracker.exe"

echo.
echo ========================================================================
echo   WHAT YOU HAVE:
echo ========================================================================
echo.
echo ✅ ONE .exe file (everything bundled inside)
if exist fx_icon.ico (
    echo ✅ Custom icon included
) else (
    echo ⚪ Default Windows icon (no fx_icon.ico found)
)
echo ✅ No Python needed to run
echo ✅ No installation required
echo ✅ Just double-click and go!
echo.
echo File size: ~50-80 MB (normal for standalone apps)
echo.
echo ========================================================================
echo   HOW TO DISTRIBUTE:
echo ========================================================================
echo.
echo 1. Go to: dist\FX Trade Tracker.exe
echo 2. Send this ONE file to your team
echo 3. They double-click it
echo 4. Dashboard opens in browser
echo 5. Done!
echo.
echo ========================================================================
echo   TEST IT NOW:
echo ========================================================================
echo.
choice /C YN /M "Do you want to test the .exe now (Y/N)"

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
echo If dashboard opened in browser - SUCCESS!
echo If not - check Windows Defender
echo.
goto END_MESSAGE

:SKIP_TEST
echo.
echo Skipped test
echo.
goto END_MESSAGE

:END_MESSAGE
echo ========================================================================
echo   IMPORTANT NOTES:
echo ========================================================================
echo.
echo WINDOWS DEFENDER WARNING:
echo   - First time you run it, Windows might show:
echo     "Windows protected your PC"
echo   - This is NORMAL for new .exe files
echo   - Click "More info" then "Run anyway"
echo.
echo FOR USERS:
echo   - Just download and double-click
echo   - No installation needed
echo   - No Python needed
echo   - Works on any Windows 10+ PC
echo.
echo YOUR .EXE IS HERE:
echo   %CD%\dist\FX Trade Tracker.exe
echo.
echo Copy this file and share with your team!
echo.
echo ========================================================================
echo.
pause

REM Open the dist folder so you can see the .exe
explorer dist

echo.
echo Build complete! Check the dist folder.
echo.