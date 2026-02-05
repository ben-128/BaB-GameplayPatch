@echo off
REM ============================================
REM Blaze & Blade - Door Modification Automation
REM ============================================
REM
REM This script:
REM 1. Applies door modifications to BLAZE.ALL
REM 2. Reinjects BLAZE.ALL into the patched BIN
REM
REM ============================================

echo.
echo ============================================
echo  Blaze ^& Blade - Door Modification
echo ============================================
echo.

REM Step 1: Apply door modifications
echo [1/2] Applying door modifications...
echo.
py -3 patch_doors.py
if errorlevel 1 (
    echo.
    echo [ERROR] Door patching failed!
    echo Check door_modifications.json
    pause
    exit /b 1
)
echo.
echo [OK] Door modifications applied to BLAZE.ALL
echo.

REM Step 2: Reinject into BIN
echo [2/2] Reinjecting BLAZE.ALL into patched BIN...
echo.
cd ..
py -3 patch_blaze_all.py
if errorlevel 1 (
    echo.
    echo [ERROR] BIN reinjection failed!
    cd level_design
    pause
    exit /b 1
)
cd level_design
echo.
echo [OK] Patched BIN created successfully!
echo.

REM Done
echo ============================================
echo  SUCCESS - All modifications applied!
echo ============================================
echo.
echo Your modified game is ready in:
echo   ..\work\patched.bin
echo.
echo Backup available at:
echo   ..\work\BLAZE.ALL.backup
echo.
pause
