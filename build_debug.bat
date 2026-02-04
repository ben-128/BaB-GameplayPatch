@echo off
echo DEBUG: Starting script...
setlocal enabledelayedexpansion
echo DEBUG: setlocal OK

cd /d "%~dp0"
echo DEBUG: cd OK

chcp 65001 >NUL
echo DEBUG: chcp OK

echo DEBUG: Creating logs directory...
if not exist "logs" mkdir logs
echo DEBUG: logs directory OK

echo DEBUG: Generating timestamp...
echo DEBUG: date = %date%
echo DEBUG: time = %time%

set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
echo DEBUG: TIMESTAMP = %TIMESTAMP%

set TIMESTAMP=%TIMESTAMP: =0%
echo DEBUG: TIMESTAMP (with 0) = %TIMESTAMP%

set LOGFILE=logs\build_%TIMESTAMP%.log
echo DEBUG: LOGFILE = %LOGFILE%

set LASTLOG=logs\last_build.log
echo DEBUG: LASTLOG = %LASTLOG%

echo DEBUG: Clearing last log...
if exist "%LASTLOG%" del "%LASTLOG%"
echo DEBUG: Last log cleared

echo DEBUG: Initializing log file...
echo. > "%LOGFILE%"
echo DEBUG: Log file initialized

echo DEBUG: Testing log function...
call :log "Test message"
echo DEBUG: Log function OK

echo.
echo ========================================
echo DEBUG TEST COMPLETE!
echo ========================================
echo.
echo If you see this, the script structure is OK.
echo Check the log file: %LOGFILE%
echo.
pause
exit /b

:log
set "MSG=%~1"
if "%MSG%"=="" (
    echo.
    echo. >> "%LOGFILE%"
) else (
    echo %MSG%
    echo %MSG% >> "%LOGFILE%"
)
goto :eof
