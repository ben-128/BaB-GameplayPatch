@echo off
cd /d "%~dp0"

echo Creating logs directory...
if not exist "logs" mkdir logs

echo Generating timestamp...
for /f %%i in ('powershell -command "Get-Date -Format yyyyMMdd_HHmm"') do set TIMESTAMP=%%i

echo Setting log path...
set LOGFILE=%~dp0logs\test_%TIMESTAMP%.log

echo LOGFILE = %LOGFILE%
echo.

echo Creating log file...
echo Test line 1 > "%LOGFILE%"
echo Test line 2 >> "%LOGFILE%"
echo Test line 3 >> "%LOGFILE%"

echo.
echo Success! Log created at:
echo %LOGFILE%
echo.

type "%LOGFILE%"

echo.
pause
