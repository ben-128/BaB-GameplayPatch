@echo off
REM ============================================
REM Lock All Doors (Test) - Quick Preset
REM ============================================

echo.
echo ============================================
echo  PRESET: Lock All Doors (TEST)
echo ============================================
echo.
echo This will:
echo   - Set all doors to KEY_LOCKED (type 1)
echo   - Require key ID 1 to open
echo.
echo WARNING: This is for TESTING purposes!
echo.
echo Press any key to continue or CTRL+C to cancel...
pause >nul
echo.

REM Copy preset
echo Copying preset configuration...
copy /Y door_presets\lock_all_doors_test.json door_modifications.json >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy preset!
    pause
    exit /b 1
)
echo [OK] Preset loaded
echo.

REM Apply modifications
call apply_door_mods.bat
