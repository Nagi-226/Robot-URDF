@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 main.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    goto :eof
)

echo Python launcher not found. Install Python 3.12 and ensure py or python is on PATH.
pause
