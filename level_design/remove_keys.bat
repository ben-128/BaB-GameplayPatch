@echo off
REM ============================================
REM Remove Key Requirements - Quick Preset
REM ============================================

echo.
echo ============================================
echo  PRESET: Remove All Key Requirements
echo ============================================
echo.
echo This will:
echo   - Keep door types (visual appearance)
echo   - Remove all key requirements (key_id = 0)
echo.
echo Press any key to continue or CTRL+C to cancel...
pause >nul
echo.

REM Copy preset
echo Copying preset configuration...
copy /Y door_presets\remove_key_requirements.json door_modifications.json >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy preset!
    pause
    exit /b 1
)
echo [OK] Preset loaded
echo.

REM Apply modifications
call apply_door_mods.bat
