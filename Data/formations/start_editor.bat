@echo off
echo ====================================
echo Zone Spawn Editor - Blaze ^& Blade
echo ====================================
echo.
echo Starting local web server...
echo.
echo Server will run on: http://localhost:8080
echo Opening browser...
echo.
echo Press Ctrl+C to stop the server when done.
echo ====================================
echo.

cd /d "%~dp0"

start http://localhost:8080/zone_spawn_editor.html

python -m http.server 8080
