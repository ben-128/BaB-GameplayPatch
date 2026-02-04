@echo off
setlocal enabledelayedexpansion

echo ========================================================================
echo   RESTORE ORIGINAL BLAZE.ALL
echo ========================================================================
echo.
echo This script will restore work\BLAZE.ALL from the most recent backup.
echo.

REM Check if work directory exists (one level up)
if not exist "..\work" (
    echo ERROR: ..\work directory not found!
    echo.
    pause
    exit /b 1
)

REM Find the most recent backup in work directory
set "latest_backup="
for /f "delims=" %%f in ('dir /b /od "..\work\BLAZE.ALL.backup_*" 2^>nul') do (
    set "latest_backup=%%f"
)

if "!latest_backup!"=="" (
    echo ERROR: No backup file found!
    echo Looking for files matching: ..\work\BLAZE.ALL.backup_*
    echo.
    pause
    exit /b 1
)

echo Found backup: !latest_backup!
echo.
echo WARNING: This will overwrite the current ..\work\BLAZE.ALL file.
echo.
pause
echo.

echo Restoring from backup...
copy /Y "..\work\!latest_backup!" "..\work\BLAZE.ALL" >nul
if errorlevel 1 (
    echo ERROR: Failed to restore backup!
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   SUCCESS!
echo ========================================================================
echo.
echo ..\work\BLAZE.ALL has been restored from: !latest_backup!
echo.
echo To apply to the BIN file, run:
echo   python ..\patch_blaze_all.py
echo.
echo ========================================================================
echo.
pause
