@echo off
setlocal enabledelayedexpansion

echo ========================================================================
echo   AUCTION PRICE MODIFICATION - TEST MODE
echo ========================================================================
echo.
echo This script will:
echo   1. Modify auction prices in BLAZE.ALL (creates backup)
echo   2. Patch the modified BLAZE.ALL into the BIN file
echo.
echo Test modifications:
echo   - Healing Potion: 10 --^> 99
echo   - Shortsword:     22 --^> 88
echo   - Leather Armor:  36 --^> 77
echo.
echo ========================================================================
echo.
pause
echo.

REM Check if work directory exists (one level up)
if not exist "..\work" (
    echo ERROR: ..\work directory not found!
    echo Please make sure the work directory exists in parent directory.
    echo.
    pause
    exit /b 1
)

REM Check if BLAZE.ALL exists in work directory
if not exist "..\work\BLAZE.ALL" (
    echo ERROR: ..\work\BLAZE.ALL not found!
    echo Please make sure BLAZE.ALL is in the work directory.
    echo.
    pause
    exit /b 1
)

REM Check if work directory and BIN exist
if not exist "..\work\Blaze & Blade - Patched.bin" (
    echo ERROR: ..\work\Blaze ^& Blade - Patched.bin not found!
    echo Please make sure the work directory exists with the BIN file.
    echo.
    pause
    exit /b 1
)

echo ========================================================================
echo   STEP 1: MODIFYING AUCTION PRICES
echo ========================================================================
echo.

python test_modify_16bit_prices.py
if errorlevel 1 (
    echo.
    echo ERROR: Price modification failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   STEP 2: PATCHING BIN FILE
echo ========================================================================
echo.

python ..\patch_blaze_all.py
if errorlevel 1 (
    echo.
    echo ERROR: BIN patching failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   SUCCESS!
echo ========================================================================
echo.
echo Modified BIN file: work\Blaze ^& Blade - Patched.bin
echo.
echo NEXT STEPS:
echo   1. Test the patched BIN in your PS1 emulator
echo   2. Go to the auction and check prices:
echo      - Healing Potion should be 99
echo      - Shortsword should be 88
echo      - Leather Armor should be 77
echo.
echo   3. If prices changed: SUCCESS! Document full item table
echo   4. If prices didn't change: Try searching other locations
echo.
echo To restore original BLAZE.ALL, check the backup files created.
echo.
echo ========================================================================
echo.
pause
