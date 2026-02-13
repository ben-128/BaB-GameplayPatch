@echo off
REM apply_trigger_test.bat
REM Applique un test de triggers et rebuild le BIN

setlocal

if "%1"=="" (
    echo.
    echo Usage: apply_trigger_test.bat N  ^(N=1-5^)
    echo.
    echo Tests disponibles:
    echo   1 - Desactive triggers 1-20
    echo   2 - Desactive triggers 21-40
    echo   3 - Desactive triggers 41-60
    echo   4 - Desactive triggers 61-80
    echo   5 - Desactive triggers 81-100
    echo.
    echo Exemple: apply_trigger_test.bat 1
    echo.
    exit /b 1
)

set GROUP=%1

REM Verifier que le groupe existe
if not exist "Data\doors\trigger_tests\LEVELS_TEST_GROUP%GROUP%.DAT" (
    echo ERREUR: Groupe %GROUP% invalide ou fichier manquant
    echo.
    echo Executez d'abord:
    echo   cd Data\doors\scripts
    echo   py -3 test_triggers_system.py patch %GROUP%
    echo.
    exit /b 1
)

echo.
echo ======================================================================
echo   APPLICATION TEST TRIGGER - GROUPE %GROUP%
echo ======================================================================
echo.

REM Backup du LEVELS.DAT original (si pas deja fait)
if not exist "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT.original" (
    echo Backup du LEVELS.DAT original...
    copy /Y "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT" "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT.original"
)

REM Copier le fichier de test
echo Copie de LEVELS_TEST_GROUP%GROUP%.DAT...
copy /Y "Data\doors\trigger_tests\LEVELS_TEST_GROUP%GROUP%.DAT" "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT"

if errorlevel 1 (
    echo ERREUR lors de la copie!
    exit /b 1
)

echo.
echo Reconstruction du BIN...
call build.bat

if errorlevel 1 (
    echo ERREUR lors du build!
    exit /b 1
)

echo.
echo ======================================================================
echo   TEST GROUPE %GROUP% PRET!
echo ======================================================================
echo.
echo TRIGGERS DESACTIVES: %GROUP%-20 a %GROUP%-40
echo.
echo PROCHAINES ETAPES:
echo   1. Lancer le jeu avec le BIN patche
echo   2. Explorer les zones (priorite: Cavern, Forest, Castle)
echo   3. Noter quelles PORTES ont disparu ou sont inaccessibles
echo   4. Consulter: Data\doors\trigger_tests\test_group%GROUP%_notes.txt
echo.
echo Pour restaurer l'original:
echo   restore_original_levels.bat
echo.
echo ======================================================================

endlocal
