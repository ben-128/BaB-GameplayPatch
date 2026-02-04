@echo off
REM ========================================================================
REM  Patch Items - Blaze & Blade: Eternal Quest
REM
REM  Ce script:
REM  1. Patch les descriptions d'items dans work/BLAZE.ALL
REM  2. Reconstruit le .bin avec mkpsxiso (si disponible)
REM ========================================================================

echo.
echo ========================================================================
echo   Patch Items - Blaze ^& Blade: Eternal Quest
echo ========================================================================
echo.

REM Aller dans le dossier items
cd /d "%~dp0items"

REM Étape 1: Patcher BLAZE.ALL
echo [Etape 1/3] Patch de BLAZE.ALL...
echo.
py -3 patch_items.py
if errorlevel 1 (
    echo.
    echo ERREUR lors du patch de BLAZE.ALL
    pause
    exit /b 1
)

echo.
echo [OK] BLAZE.ALL patche avec succes
echo.

REM Étape 2: Vérifier si mkpsxiso est disponible
echo [Etape 2/3] Verification de mkpsxiso...
where mkpsxiso >nul 2>&1
if errorlevel 1 (
    echo.
    echo ATTENTION: mkpsxiso non trouve dans PATH
    echo.
    echo Pour appliquer le patch au .bin, vous devez:
    echo   1. Installer mkpsxiso: https://github.com/Lameguy64/mkpsxiso
    echo   2. Extraire le .bin avec: mkpsxiso -x "Blaze and Blade - Eternal Quest (E).bin"
    echo   3. Copier work/BLAZE.ALL dans le dossier extrait
    echo   4. Rebuilder avec: mkpsxiso -y "project.xml" -o "Blaze and Blade - Eternal Quest (E) [Patched].bin"
    echo.
    goto :end_patch
)

echo mkpsxiso trouve
echo.

REM Étape 3: Extraire et rebuilder le .bin (si mkpsxiso disponible)
echo [Etape 3/3] Extraction et rebuild du .bin...
echo.

cd /d "%~dp0"

REM Vérifier si le .bin existe
if not exist "Blaze and Blade - Eternal Quest (E).bin" (
    echo ERREUR: "Blaze and Blade - Eternal Quest (E).bin" non trouve
    echo.
    goto :end_patch
)

REM Créer un dossier temp pour l'extraction
if not exist "temp_iso" mkdir temp_iso

echo Extraction du .bin...
mkpsxiso -x "Blaze and Blade - Eternal Quest (E).bin" -o temp_iso
if errorlevel 1 (
    echo ERREUR lors de l'extraction
    goto :end_patch
)

REM Copier le BLAZE.ALL patché
echo.
echo Copie de BLAZE.ALL patche...
copy /Y "work\BLAZE.ALL" "temp_iso\BLAZE.ALL"

REM Rebuilder le .bin
echo.
echo Rebuild du .bin...
mkpsxiso -y "temp_iso\project.xml" -o "Blaze and Blade - Eternal Quest (E) [Items Patched].bin"
if errorlevel 1 (
    echo ERREUR lors du rebuild
    goto :end_patch
)

echo.
echo [OK] .bin patche cree: "Blaze and Blade - Eternal Quest (E) [Items Patched].bin"
echo.

:end_patch
echo.
echo ========================================================================
echo   Patch termine
echo ========================================================================
echo.
echo FICHIERS CREES:
echo   - work\BLAZE.ALL.backup (backup original)
echo   - work\BLAZE.ALL (patche)
if exist "Blaze and Blade - Eternal Quest (E) [Items Patched].bin" (
    echo   - "Blaze and Blade - Eternal Quest (E) [Items Patched].bin"
)
echo.
pause
