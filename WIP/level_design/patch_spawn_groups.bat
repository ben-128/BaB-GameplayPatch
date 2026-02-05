@echo off
cd /d "%~dp0..\.."
echo ======================================================================
echo   Patch Spawn Groups into BLAZE.ALL
echo ======================================================================
echo.
py -3 WIP\level_design\patch_spawn_groups.py
echo.
pause
