@echo off
REM ========================================================================
REM  Patch Items - Blaze & Blade: Eternal Quest
REM
REM  Ce script:
REM  1. Patch les descriptions d'items dans work/BLAZE.ALL
REM  2. Patch les descriptions d'items dans work/patched.bin
REM
REM  Localisation: items/patch_items_to_bin.bat
REM ========================================================================

echo.
echo ========================================================================
echo   Patch Items - Blaze ^& Blade: Eternal Quest
echo ========================================================================
echo.

REM Deja dans le dossier items
cd /d "%~dp0"

REM Patcher BLAZE.ALL et patched.bin
echo Patch de work/BLAZE.ALL et work/patched.bin...
echo.
py -3 patch_items_in_bin.py
if errorlevel 1 (
    echo.
    echo ERREUR lors du patch
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   Patch termine avec succes!
echo ========================================================================
echo.
echo Fichiers patches:
echo   - work/BLAZE.ALL
echo   - work/patched.bin
echo.
echo Items patches: 294/316 items (93%%)
echo Abbreviations: STR=S+, INT=I+, WIL=W+, AGL=A+, CON=C+, POW=P+, LUK=L+, MAT=MA+, MDEF=MD+
echo.
pause
