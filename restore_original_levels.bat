@echo off
REM restore_original_levels.bat
REM Restaure le LEVELS.DAT original et rebuild

echo.
echo ======================================================================
echo   RESTAURATION LEVELS.DAT ORIGINAL
echo ======================================================================
echo.

if not exist "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT.original" (
    echo ERREUR: Backup original introuvable!
    echo Aucun backup LEVELS.DAT.original trouve.
    echo.
    exit /b 1
)

echo Restauration du fichier original...
copy /Y "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT.original" "Blaze  Blade - Eternal Quest (Europe)\extract\LEVELS.DAT"

if errorlevel 1 (
    echo ERREUR lors de la restauration!
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
echo   LEVELS.DAT ORIGINAL RESTAURE!
echo ======================================================================
echo.
echo Le jeu utilise maintenant le fichier original.
echo.
