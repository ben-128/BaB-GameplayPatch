@echo off
REM ============================================
REM Unlock All Doors - Quick Preset
REM ============================================

echo.
echo ============================================
echo  PRESET: Unlock All Doors
echo ============================================
echo.
echo This will:
echo   - Set all doors to UNLOCKED (type 0)
echo   - Remove all key requirements
echo.
echo Press any key to continue or CTRL+C to cancel...
pause >nul
echo.

REM Copy preset
echo Copying preset configuration...
copy /Y ..\data\presets\unlock_all_doors.json ..\data\door_modifications.json >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy preset!
    pause
    exit /b 1
)
echo [OK] Preset loaded
echo.

REM Apply modifications
call apply_door_mods.bat
