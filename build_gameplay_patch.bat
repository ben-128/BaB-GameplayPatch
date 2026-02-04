@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >NUL

echo ============================================
echo  Bab Gameplay Patch Builder
echo ============================================
echo.

REM Step 1: Patch Fate Coin Shop prices into BLAZE.ALL
echo [1/3] Patching Fate Coin Shop prices...
py -3 fate_coin_shop\patch_fate_coin_shop.py
if errorlevel 1 goto :error

echo.

REM Step 2: Inject BLAZE.ALL into BIN
echo [2/3] Injecting BLAZE.ALL into BIN...
py -3 patch_blaze_all.py
if errorlevel 1 goto :error

echo.

REM Step 3: Patch monster stats directly into BIN
echo [3/3] Patching monster stats into BIN...
py -3 monster_stats\patch_monster_stats_bin.py
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
