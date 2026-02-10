@echo off
setlocal
cd /d "%~dp0"
REM chcp 65001 >NUL

REM ========================================================================
REM Optional patches (set to 1 to enable)
REM ========================================================================
set PATCH_LOOT_TIMER=1

REM ========================================================================
REM Initialize logging
REM ========================================================================

REM Create logs directory if it doesn't exist
if not exist "output\logs" mkdir "output\logs"

REM Generate log filename with simple counter
for /f %%i in ('powershell -command "Get-Date -Format yyyyMMdd_HHmm"') do set TIMESTAMP=%%i
set LOGFILE=%~dp0output\logs\build_%TIMESTAMP%.log
set LASTLOG=%~dp0output\output\logs\last_build.log

echo Initializing build system...
echo Log file: %LOGFILE%

REM Clear last log
if exist "%LASTLOG%" del "%LASTLOG%"

REM Initialize log file
(
echo ========================================================================
echo   Bab Gameplay Patch Builder - Complete Edition
echo ========================================================================
echo.
echo Build started: %date% %time%
echo.
echo Ce script va:
echo   1. Copier BLAZE.ALL clean depuis extract vers work
echo   2. Patcher les prix Fate Coin Shop dans BLAZE.ALL
echo   3. Patcher les descriptions d'items dans BLAZE.ALL
echo   4. Patcher les prix d'enchere - base a 0 - dans BLAZE.ALL
echo   5. Patcher les stats des monstres dans BLAZE.ALL
echo   6. Patcher les spawns de monstres dans BLAZE.ALL
echo   7. Patcher le timer de disparition des coffres dans BLAZE.ALL (optionnel, desactive)
echo   8. Creer le BIN patche a partir du BIN clean original
echo   9. Injecter BLAZE.ALL dans le BIN (2 emplacements)
echo  10. Mettre a jour la documentation
echo.
echo ========================================================================
echo.
) > "%LOGFILE%" 2>&1

REM Display same on console
type "%LOGFILE%"

REM ========================================================================
REM Step 1: Copy clean BLAZE.ALL from extract to work
REM ========================================================================
call :log "[1/10] Copying clean BLAZE.ALL from extract to work..."
call :log ""

set CLEAN_BLAZE=%~dp0Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL
set WORK_BLAZE=%~dp0output\BLAZE.ALL

if not exist "%CLEAN_BLAZE%" (
    call :log "[ERROR] Clean BLAZE.ALL not found: %CLEAN_BLAZE%"
    goto :error
)

copy /Y "%CLEAN_BLAZE%" "%WORK_BLAZE%" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Failed to copy clean BLAZE.ALL!"
    goto :error
)

call :log ""
call :log "[OK] Clean BLAZE.ALL copied to work folder"
call :log ""

REM ========================================================================
REM Step 2: Patch Fate Coin Shop prices
REM ========================================================================
call :log "[2/10] Patching Fate Coin Shop prices..."
call :log ""

py -3 Data\fate_coin_shop\patch_fate_coin_shop.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Fate Coin Shop patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Fate Coin Shop prices patched"
call :log ""

REM ========================================================================
REM Step 3: Patch Items descriptions
REM ========================================================================
call :log "[3/10] Patching Items descriptions in BLAZE.ALL..."
call :log ""

cd Data\items
py -3 patch_items_in_bin.py > "%TEMP%\items_patch_output.txt" 2>&1
set ITEMS_ERRORLEVEL=%errorlevel%
type "%TEMP%\items_patch_output.txt" >> "%LOGFILE%"
cd ..\..

if %ITEMS_ERRORLEVEL% neq 0 (
    call :log ""
    call :log "[ERROR] Items patch failed!"
    goto :error
)

REM Extract patched count from output
set ITEMS_PATCHED=0
for /f "tokens=2 delims==" %%a in ('findstr "PATCHED_COUNT=" "%TEMP%\items_patch_output.txt"') do set ITEMS_PATCHED=%%a

call :log ""
call :log "[OK] Items descriptions patched (%ITEMS_PATCHED% items)"
call :log ""

REM ========================================================================
REM Step 4: Patch auction base prices to 0
REM ========================================================================
call :log "[4/10] Patching auction base prices (set to 0)..."
call :log ""

py -3 Data\auction_prices\patch_auction_base_prices.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Auction base prices patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Auction base prices set to 0"
call :log ""

REM ========================================================================
REM Step 5: Patch monster stats in BLAZE.ALL
REM ========================================================================
call :log "[5/10] Patching monster stats in BLAZE.ALL..."
call :log ""

py -3 Data\monster_stats\scripts\patch_monster_stats.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Monster stats patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Monster stats patched in BLAZE.ALL"
call :log ""

REM ========================================================================
REM Step 6: Patch monster spawn groups in BLAZE.ALL
REM ========================================================================
call :log "[6/10] Patching monster spawn groups in BLAZE.ALL..."
call :log ""

py -3 WIP\level_design\spawns\scripts\patch_spawn_groups.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Monster spawn groups patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Monster spawn groups patched in BLAZE.ALL"
call :log ""

REM ========================================================================
REM Step 6b: Patch formation templates in BLAZE.ALL
REM ========================================================================
call :log "[6b/10] Patching formation templates in BLAZE.ALL..."
call :log ""

py -3 Data\formations\patch_formations.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Formation templates patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Formation templates patched in BLAZE.ALL"
call :log ""

REM ========================================================================
REM Step 7: Patch chest despawn timer in BLAZE.ALL overlay code (OPTIONAL)
REM ========================================================================
if "%PATCH_LOOT_TIMER%"=="1" (
    call :log "[7/10] Patching chest despawn timer in overlay code..."
    call :log ""

    py -3 Data\LootTimer\patch_loot_timer.py >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        call :log ""
        call :log "[ERROR] Loot timer overlay patch failed!"
        goto :error
    )

    call :log ""
    call :log "[OK] Chest despawn timer patched in overlay code"
    call :log ""
) else (
    call :log "[7/10] Chest despawn timer patch SKIPPED (set PATCH_LOOT_TIMER=1 to enable)"
    call :log ""
)

REM ========================================================================
REM Step 7b: Patch spell table entries in BLAZE.ALL
REM ========================================================================
call :log "[7b/10] Patching spell table entries in BLAZE.ALL..."
call :log ""

py -3 Data\monster_stats\patch_spell_table.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Spell table patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Spell table entries processed"
call :log ""

REM ========================================================================
REM Step 7c: Patch AI behavior blocks in BLAZE.ALL
REM ========================================================================
call :log "[7c/10] Patching AI behavior blocks in BLAZE.ALL..."
call :log ""

py -3 Data\ai_behavior\patch_ai_behavior.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] AI behavior patch failed!"
    goto :error
)

call :log ""
call :log "[OK] AI behavior blocks processed"
call :log ""

REM ========================================================================
REM Step 7d: Patch trap/environmental damage in BLAZE.ALL
REM ========================================================================
call :log "[7d/10] Patching trap damage in BLAZE.ALL..."
call :log ""

py -3 Data\trap_damage\patch_trap_damage.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Trap damage patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Trap damage processed"
call :log ""

REM ========================================================================
REM Step 8: Create fresh patched BIN from clean original
REM ========================================================================
call :log "[8/10] Creating fresh patched BIN from clean original..."
call :log ""

set CLEAN_BIN=%~dp0Blaze  Blade - Eternal Quest (Europe)\Blaze ^& Blade - Eternal Quest (Europe).bin
set PATCHED_BIN=%~dp0output\Blaze ^& Blade - Patched.bin

if not exist "%CLEAN_BIN%" (
    call :log "[ERROR] Clean BIN not found: %CLEAN_BIN%"
    goto :error
)

copy /Y "%CLEAN_BIN%" "%PATCHED_BIN%" >> "%LOGFILE%" 2>&1

if not exist "%PATCHED_BIN%" (
    call :log ""
    call :log "[ERROR] Failed to copy clean BIN!"
    goto :error
)

call :log ""
call :log "[OK] Fresh patched BIN created from clean original"
call :log ""

REM ========================================================================
REM Step 9: Inject BLAZE.ALL into BIN (2 locations)
REM ========================================================================
call :log "[9/10] Injecting BLAZE.ALL into BIN (2 locations)..."
call :log ""

py -3 patch_blaze_all.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] BLAZE.ALL injection failed!"
    goto :error
)

call :log ""
call :log "[OK] BLAZE.ALL injected into BIN"
call :log ""

REM ========================================================================
REM Step 9b: (Loot timer now patches BLAZE.ALL at step 7)
REM ========================================================================
if "%PATCH_LOOT_TIMER%"=="1" (
    call :log "[9b/10] Loot timer: already patched in BLAZE.ALL at step 7"
) else (
    call :log "[9b/10] Loot timer: skipped"
)
call :log ""

REM ========================================================================
REM Step 9c: Patch monster spell assignments in SLES (EXE inside BIN)
REM ========================================================================
call :log "[9c/10] Patching monster spell assignments in EXE..."
call :log ""

py -3 Data\monster_stats\patch_monster_spells.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Monster spell assignment patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Monster spell assignments processed"
call :log ""

REM ========================================================================
REM Step 10: Update documentation
REM ========================================================================
call :log "[10/10] Updating documentation..."
call :log ""

py -3 -c "from pathlib import Path; from datetime import datetime; import sys; items_count = sys.argv[1]; readme = Path('README.md'); content = readme.read_text(encoding='utf-8'); patch_info = f'\n## Last Patch Build\n\n**Date:** {datetime.now().strftime(\"%%Y-%%m-%%d %%H:%%M:%%S\")}\n\n**Patches Applied:**\n- Fate Coin Shop prices adjusted\n- Items descriptions updated ({items_count} items)\n- Auction base prices set to 0\n- Monster stats balanced\n- BLAZE.ALL integrated\n\n**Source:** Blaze & Blade - Eternal Quest (Europe).bin\n**Output:** output/Blaze & Blade - Patched.bin\n\n'; import re; content = re.sub(r'## Last Patch Build.*?(?=##|\Z)', patch_info, content, flags=re.DOTALL) if '## Last Patch Build' in content else content + patch_info; readme.write_text(content, encoding='utf-8'); print('[OK] README.md updated')" %ITEMS_PATCHED% >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    call :log "[WARNING] Could not update README.md"
) else (
    call :log "[OK] README.md updated"
)

call :log ""

REM ========================================================================
REM Success!
REM ========================================================================
call :log "========================================================================"
call :log "  Build Complete!"
call :log "========================================================================"
call :log ""
call :log "Build finished: %date% %time%"
call :log ""
call :log "Fichiers crees:"
call :log "  - output/BLAZE.ALL (patched)"
call :log "  - output/Blaze ^& Blade - Patched.bin (ready for game)"
call :log ""
call :log "Source:"
call :log "  - Blaze ^& Blade - Eternal Quest (Europe).bin (clean original)"
call :log ""
call :log "Le patch est pret pour le test en jeu!"
call :log ""
call :log "Log file: %LOGFILE%"
call :log ""

REM Copy to last_build.log for easy access
copy /Y "%LOGFILE%" "%LASTLOG%" >NUL 2>&1

goto :end

:error
call :log ""
call :log "========================================================================"
call :log "  ERROR: Build failed!"
call :log "========================================================================"
call :log ""
call :log "Build failed: %date% %time%"
call :log ""
call :log "Verifiez les logs ci-dessus pour plus de details."
call :log "Log file: %LOGFILE%"
call :log ""

REM Copy to last_build.log even on error
copy /Y "%LOGFILE%" "%LASTLOG%" >NUL 2>&1

:end
echo.
if exist "%LOGFILE%" (
    echo Log file saved: %LOGFILE%
    echo Quick access: output\logs\last_build.log
) else (
    echo WARNING: Log file was not created
)
echo.
pause

REM ========================================================================
REM Logging function - writes to both console and log file
REM ========================================================================
:log
if "%~1"=="" (
    echo.
    echo. >> "%LOGFILE%" 2>nul
) else (
    <nul set /p "=.%~1" & echo.
    <nul set /p "=.%~1" >> "%LOGFILE%" 2>nul & echo. >> "%LOGFILE%" 2>nul
)
goto :eof
