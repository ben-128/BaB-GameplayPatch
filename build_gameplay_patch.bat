@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
chcp 65001 >NUL

REM ========================================================================
REM Initialize logging
REM ========================================================================

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Generate log filename with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set LOGFILE=logs\build_%mydate%_%mytime%.log
set LASTLOG=logs\last_build.log

REM Clear last log
if exist "%LASTLOG%" del "%LASTLOG%"

REM Initialize log file
echo. > "%LOGFILE%"

REM Start logging
call :log ""
call :log "========================================================================"
call :log "  Bab Gameplay Patch Builder - Complete Edition"
call :log "========================================================================"
call :log ""
call :log "Build started: %date% %time%"
call :log "Log file: %LOGFILE%"
call :log ""
call :log "Ce script va:"
call :log "  1. Patcher les prix Fate Coin Shop"
call :log "  2. Patcher les descriptions d'items"
call :log "  3. Injecter BLAZE.ALL dans le BIN"
call :log "  4. Patcher les stats des monstres"
call :log "  5. Mettre a jour la documentation"
call :log "  6. Commit et polish"
call :log ""
call :log "========================================================================"
call :log ""

REM ========================================================================
REM Step 1: Patch Fate Coin Shop prices
REM ========================================================================
call :log "[1/6] Patching Fate Coin Shop prices..."
call :log ""

py -3 fate_coin_shop\patch_fate_coin_shop.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Fate Coin Shop patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Fate Coin Shop prices patched"
call :log ""

REM ========================================================================
REM Step 2: Patch Items descriptions
REM ========================================================================
call :log "[2/6] Patching Items descriptions (BLAZE.ALL + patched.bin)..."
call :log ""

cd items
py -3 patch_items_in_bin.py >> "..\%LOGFILE%" 2>&1
set ITEMS_ERRORLEVEL=%errorlevel%
cd ..

if %ITEMS_ERRORLEVEL% neq 0 (
    call :log ""
    call :log "[ERROR] Items patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Items descriptions patched (294 items)"
call :log ""

REM ========================================================================
REM Step 3: Inject BLAZE.ALL into BIN
REM ========================================================================
call :log "[3/6] Injecting BLAZE.ALL into BIN..."
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
REM Step 4: Patch monster stats
REM ========================================================================
call :log "[4/6] Patching monster stats into BIN..."
call :log ""

py -3 monster_stats\patch_monster_stats_bin.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log ""
    call :log "[ERROR] Monster stats patch failed!"
    goto :error
)

call :log ""
call :log "[OK] Monster stats patched"
call :log ""

REM ========================================================================
REM Step 5: Update documentation
REM ========================================================================
call :log "[5/6] Updating documentation..."
call :log ""

py -3 -c "from pathlib import Path; from datetime import datetime; readme = Path('README.md'); content = readme.read_text(encoding='utf-8'); patch_info = f'\n## Last Patch Build\n\n**Date:** {datetime.now().strftime(\"%%Y-%%m-%%d %%H:%%M:%%S\")}\n\n**Patches Applied:**\n- Fate Coin Shop prices adjusted\n- Items descriptions updated (294 items)\n- Monster stats balanced\n- BLAZE.ALL integrated\n\n**Output:** work/patched.bin\n\n'; import re; content = re.sub(r'## Last Patch Build.*?(?=##|\Z)', patch_info, content, flags=re.DOTALL) if '## Last Patch Build' in content else content + patch_info; readme.write_text(content, encoding='utf-8'); print('[OK] README.md updated')" >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    call :log "[WARNING] Could not update README.md"
) else (
    call :log "[OK] README.md updated"
)

call :log ""

REM ========================================================================
REM Step 6: Commit and polish
REM ========================================================================
call :log "[6/6] Commit and polish..."
call :log ""

git diff --quiet
if errorlevel 1 (
    call :log "Git changes detected, committing..."

    git add . >> "%LOGFILE%" 2>&1

    git commit -m "Build gameplay patch - Auto-generated

Patches applied:
- Fate Coin Shop prices
- Items descriptions (294 items with MA+/MD+ abbreviations)
- Monster stats balancing
- Documentation updated

Output: work/patched.bin ready for testing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>" >> "%LOGFILE%" 2>&1

    if errorlevel 1 (
        call :log "[WARNING] Git commit failed"
    ) else (
        call :log "[OK] Changes committed"
    )
) else (
    call :log "[INFO] No changes to commit"
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
call :log "  - work/BLAZE.ALL (patched)"
call :log "  - work/patched.bin (patched, ready for game)"
call :log ""
call :log "Backups:"
call :log "  - work/BLAZE.ALL.backup"
call :log "  - work/patched.bin.backup"
call :log ""
call :log "Items patches: 294/316 items (93%%)"
call :log "Abbreviations: STR=S+, INT=I+, WIL=W+, AGL=A+, CON=C+, POW=P+, LUK=L+, MAT=MA+, MDEF=MD+"
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
echo Log file saved: %LOGFILE%
echo Quick access: logs\last_build.log
echo.
pause
exit /b

REM ========================================================================
REM Logging function - writes to both console and log file
REM ========================================================================
:log
set "MSG=%~1"
if "%MSG%"=="" (
    echo.
    echo. >> "%LOGFILE%"
) else (
    echo %MSG%
    echo %MSG% >> "%LOGFILE%"
)
goto :eof
