@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >NUL

echo.
echo ========================================================================
echo  Bab Gameplay Patch Builder - Complete Edition
echo ========================================================================
echo.
echo Ce script va:
echo   1. Patcher les prix Fate Coin Shop
echo   2. Patcher les descriptions d'items
echo   3. Injecter BLAZE.ALL dans le BIN
echo   4. Patcher les stats des monstres
echo   5. Mettre a jour la documentation
echo   6. Commit et polish
echo.
echo ========================================================================
echo.

REM ========================================================================
REM Step 1: Patch Fate Coin Shop prices
REM ========================================================================
echo [1/6] Patching Fate Coin Shop prices...
echo.
py -3 fate_coin_shop\patch_fate_coin_shop.py
if errorlevel 1 goto :error
echo.
echo [OK] Fate Coin Shop prices patched
echo.

REM ========================================================================
REM Step 2: Patch Items descriptions
REM ========================================================================
echo [2/6] Patching Items descriptions (BLAZE.ALL + patched.bin)...
echo.
cd items
py -3 patch_items_in_bin.py
if errorlevel 1 goto :error
cd ..
echo.
echo [OK] Items descriptions patched (294 items)
echo.

REM ========================================================================
REM Step 3: Inject BLAZE.ALL into BIN
REM ========================================================================
echo [3/6] Injecting BLAZE.ALL into BIN...
echo.
py -3 patch_blaze_all.py
if errorlevel 1 goto :error
echo.
echo [OK] BLAZE.ALL injected into BIN
echo.

REM ========================================================================
REM Step 4: Patch monster stats
REM ========================================================================
echo [4/6] Patching monster stats into BIN...
echo.
py -3 monster_stats\patch_monster_stats_bin.py
if errorlevel 1 goto :error
echo.
echo [OK] Monster stats patched
echo.

REM ========================================================================
REM Step 5: Update documentation
REM ========================================================================
echo [5/6] Updating documentation...
echo.

REM Update README.md with patch summary
py -3 -c "
from pathlib import Path
from datetime import datetime

readme = Path('README.md')
content = readme.read_text(encoding='utf-8')

# Add/update patch info section
patch_info = f'''
## Last Patch Build

**Date:** {datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S')}

**Patches Applied:**
- Fate Coin Shop prices adjusted
- Items descriptions updated (294 items)
- Monster stats balanced
- BLAZE.ALL integrated

**Output:** work/patched.bin

'''

# Find or create patch info section
if '## Last Patch Build' in content:
    # Replace existing section
    import re
    content = re.sub(
        r'## Last Patch Build.*?(?=##|\Z)',
        patch_info,
        content,
        flags=re.DOTALL
    )
else:
    # Add at the end
    content += '\n' + patch_info

readme.write_text(content, encoding='utf-8')
print('[OK] README.md updated')
"

if errorlevel 1 (
    echo [WARNING] Could not update README.md
)

echo.

REM ========================================================================
REM Step 6: Commit and polish
REM ========================================================================
echo [6/6] Commit and polish...
echo.

REM Check if there are changes to commit
git diff --quiet
if errorlevel 1 (
    echo Git changes detected, committing...

    git add .

    git commit -m "Build gameplay patch - Auto-generated

Patches applied:
- Fate Coin Shop prices
- Items descriptions (294 items with MA+/MD+ abbreviations)
- Monster stats balancing
- Documentation updated

Output: work/patched.bin ready for testing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    if errorlevel 1 (
        echo [WARNING] Git commit failed
    ) else (
        echo [OK] Changes committed
    )
) else (
    echo [INFO] No changes to commit
)

echo.

REM ========================================================================
REM Success!
REM ========================================================================
echo ========================================================================
echo  Build Complete!
echo ========================================================================
echo.
echo Fichiers crees:
echo   - work/BLAZE.ALL (patched)
echo   - work/patched.bin (patched, ready for game)
echo.
echo Backups:
echo   - work/BLAZE.ALL.backup
echo   - work/patched.bin.backup
echo.
echo Items patches: 294/316 items (93%%)
echo Abbreviations: STR=S+, INT=I+, WIL=W+, AGL=A+, CON=C+, POW=P+, LUK=L+, MAT=MA+, MDEF=MD+
echo.
echo Le patch est pret pour le test en jeu!
echo.
goto :end

:error
echo.
echo ========================================================================
echo  ERROR: Build failed!
echo ========================================================================
echo.
echo Verifiez les logs ci-dessus pour plus de details.
echo.

:end
pause
