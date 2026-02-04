@echo off
setlocal enabledelayedexpansion

REM Initialize status variables
set "STEP1_STATUS=PENDING"
set "STEP2_STATUS=PENDING"
set "BACKUP_FILE="
set "START_TIME=%TIME%"

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

echo [CHECK] Verifying prerequisites...
echo.

REM Check if work directory exists (one level up)
if not exist "..\work" (
    echo [ERROR] ..\work directory not found!
    echo         Please make sure the work directory exists in parent directory.
    echo.
    goto :error_end
)
echo [OK] Found work directory

REM Check if BLAZE.ALL exists in work directory
if not exist "..\work\BLAZE.ALL" (
    echo [ERROR] ..\work\BLAZE.ALL not found!
    echo         Please make sure BLAZE.ALL is in the work directory.
    echo.
    goto :error_end
)
echo [OK] Found BLAZE.ALL

REM Check if work directory and BIN exist
if not exist "..\work\Blaze & Blade - Patched.bin" (
    echo [ERROR] ..\work\Blaze ^& Blade - Patched.bin not found!
    echo         Please make sure the work directory exists with the BIN file.
    echo.
    goto :error_end
)
echo [OK] Found Blaze ^& Blade - Patched.bin

REM Get original file sizes
for %%A in ("..\work\BLAZE.ALL") do set "BLAZE_SIZE_BEFORE=%%~zA"
for %%A in ("..\work\Blaze & Blade - Patched.bin") do set "BIN_SIZE_BEFORE=%%~zA"

echo.
echo [INFO] BLAZE.ALL size: %BLAZE_SIZE_BEFORE% bytes
echo [INFO] BIN size: %BIN_SIZE_BEFORE% bytes
echo.

echo ========================================================================
echo   STEP 1/2: MODIFYING AUCTION PRICES IN BLAZE.ALL
echo ========================================================================
echo.
echo [START] Executing test_modify_16bit_prices.py...
echo.

python test_modify_16bit_prices.py
if errorlevel 1 (
    set "STEP1_STATUS=FAILED"
    echo.
    echo [ERROR] Price modification failed!
    echo [FAILED] Step 1 did not complete successfully
    echo.
    goto :show_summary
) else (
    set "STEP1_STATUS=SUCCESS"
    echo.
    echo [SUCCESS] Price modification completed

    REM Try to find the backup file
    for /f "delims=" %%f in ('dir /b /od "..\work\BLAZE.ALL.backup_*" 2^>nul') do (
        set "BACKUP_FILE=%%f"
    )
    if defined BACKUP_FILE (
        echo [INFO] Backup created: !BACKUP_FILE!
    )

    REM Verify BLAZE.ALL was modified
    for %%A in ("..\work\BLAZE.ALL") do set "BLAZE_SIZE_AFTER=%%~zA"
    if "%BLAZE_SIZE_BEFORE%"=="%BLAZE_SIZE_AFTER%" (
        echo [OK] BLAZE.ALL size unchanged: %BLAZE_SIZE_AFTER% bytes
    ) else (
        echo [WARNING] BLAZE.ALL size changed: %BLAZE_SIZE_BEFORE% -^> %BLAZE_SIZE_AFTER% bytes
    )
)

echo.
echo ========================================================================
echo   STEP 2/2: PATCHING BIN FILE
echo ========================================================================
echo.
echo [START] Executing patch_blaze_all.py...
echo.

python ..\patch_blaze_all.py
if errorlevel 1 (
    set "STEP2_STATUS=FAILED"
    echo.
    echo [ERROR] BIN patching failed!
    echo [FAILED] Step 2 did not complete successfully
    echo.
    goto :show_summary
) else (
    set "STEP2_STATUS=SUCCESS"
    echo.
    echo [SUCCESS] BIN patching completed

    REM Verify BIN was modified
    for %%A in ("..\work\Blaze & Blade - Patched.bin") do set "BIN_SIZE_AFTER=%%~zA"
    if "%BIN_SIZE_BEFORE%"=="%BIN_SIZE_AFTER%" (
        echo [OK] BIN size unchanged: %BIN_SIZE_AFTER% bytes
    ) else (
        echo [WARNING] BIN size changed: %BIN_SIZE_BEFORE% -^> %BIN_SIZE_AFTER% bytes
    )
)

:show_summary
set "END_TIME=%TIME%"

echo.
echo ========================================================================
echo   EXECUTION SUMMARY
echo ========================================================================
echo.
echo Start time:  %START_TIME%
echo End time:    %END_TIME%
echo.
echo STEP 1 - Price Modification:  [%STEP1_STATUS%]
echo STEP 2 - BIN Patching:         [%STEP2_STATUS%]
echo.

if "%STEP1_STATUS%"=="SUCCESS" if "%STEP2_STATUS%"=="SUCCESS" (
    echo ========================================================================
    echo   ALL STEPS COMPLETED SUCCESSFULLY!
    echo ========================================================================
    echo.
    echo Modified files:
    echo   - ..\work\BLAZE.ALL
    echo   - ..\work\Blaze ^& Blade - Patched.bin
    echo.
    if defined BACKUP_FILE (
        echo Backup file:
        echo   - ..\work\!BACKUP_FILE!
        echo.
    )
    echo Modified prices at 0x002EA500:
    echo   [Word 0]  Healing Potion: 10 --^> 99
    echo   [Word 2]  Shortsword:     22 --^> 88
    echo   [Word 13] Leather Armor:  36 --^> 77
    echo.
    echo ========================================================================
    echo   NEXT STEPS - TESTING IN GAME
    echo ========================================================================
    echo.
    echo 1. Load the patched BIN in your PS1 emulator:
    echo    File: ..\work\Blaze ^& Blade - Patched.bin
    echo.
    echo 2. Go to the auction and check these prices:
    echo    - Healing Potion should be 99 gold  (was 10)
    echo    - Shortsword should be 88 gold      (was 22)
    echo    - Leather Armor should be 77 gold   (was 36)
    echo.
    echo 3. Report results:
    echo    - If prices changed: SUCCESS! This is the correct location!
    echo    - If prices unchanged: This location is not auction prices
    echo.
    echo 4. To restore original BLAZE.ALL:
    if defined BACKUP_FILE (
        echo    Run: restore_original.bat
    ) else (
        echo    Backup file not found - check ..\work\ directory
    )
    echo.
    goto :end
) else (
    echo ========================================================================
    echo   EXECUTION FAILED
    echo ========================================================================
    echo.
    echo One or more steps failed. Please check the errors above.
    echo.
    if "%STEP1_STATUS%"=="FAILED" (
        echo Failed at: STEP 1 - Price Modification
        echo Check: Python script test_modify_16bit_prices.py
    )
    if "%STEP2_STATUS%"=="FAILED" (
        echo Failed at: STEP 2 - BIN Patching
        echo Check: Python script patch_blaze_all.py
    )
    echo.
    goto :error_end
)

:error_end
echo ========================================================================
pause
exit /b 1

:end
echo ========================================================================
echo.
pause
exit /b 0
