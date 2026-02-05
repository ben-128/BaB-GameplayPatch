@echo off
cd /d "%~dp0..\.."
echo ======================================================================
echo   Extract Spawn Groups from BLAZE.ALL
echo ======================================================================
echo.
py -3 WIP\level_design\extract_spawn_groups.py
echo.
pause
