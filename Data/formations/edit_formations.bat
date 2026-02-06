@echo off
echo Starting formation editor on http://localhost:8000
echo Press Ctrl+C to stop.
start http://localhost:8000
py -3 "%~dp0serve_editor.py"
pause
