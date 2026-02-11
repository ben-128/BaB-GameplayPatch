@echo off
setlocal
cd /d "%~dp0"

echo ========================================================================
echo   SPELL OFFSET FREEZE TEST - Quick Build
echo ========================================================================
echo.
echo This creates a minimal test BIN with a freeze at spell init offset.
echo Use this to verify if offset 0x0092BF74 executes during combat.
echo.
echo WARNING: The game will FREEZE during Cavern of Death combat!
echo.
pause

echo.
echo [1/4] Copying clean BLAZE.ALL...
copy /Y "Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL" "output\BLAZE.ALL" >NUL

echo [2/4] Patching BLAZE.ALL with freeze...
py -3 Data\ai_behavior\patch_spell_freeze_test.py

echo.
echo [3/4] Copying clean BIN...
copy /Y "Blaze  Blade - Eternal Quest (Europe)\Blaze & Blade - Eternal Quest (Europe).bin" "output\Blaze & Blade - Patched.bin" >NUL

echo [4/4] Injecting BLAZE.ALL into BIN...
py -3 patch_blaze_all.py

echo.
echo ========================================================================
echo   TEST BIN READY
echo ========================================================================
echo.
echo Output: output\Blaze ^& Blade - Patched.bin
echo.
echo TEST PROCEDURE:
echo   1. Load output\Blaze ^& Blade - Patched.bin in emulator
echo   2. Start game (or load save)
echo   3. Go to Cavern of Death Floor 1
echo   4. Walk until combat triggers
echo.
echo EXPECTED RESULTS:
echo   - Game FREEZES at combat start = Offset CORRECT (can implement patch!)
echo   - Game runs normally = Offset wrong/dead (need new approach)
echo.
pause
