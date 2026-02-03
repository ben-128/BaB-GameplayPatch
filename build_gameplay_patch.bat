@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >NUL

echo ============================================
echo  Bab Gameplay Patch Builder
echo ============================================
echo.

REM Patch monster stats directly into BIN (patches both data copies)
echo [1/1] Patching monster stats into BIN...
py -3 patch_monster_stats_bin.py
if errorlevel 1 goto :error

echo.
echo ============================================
echo  Build complete!
echo  Output: work\Blaze ^& Blade - Patched.bin
echo ============================================
goto :end

:error
echo.
echo ============================================
echo  ERROR: Build failed!
echo ============================================

:end
echo.
pause
