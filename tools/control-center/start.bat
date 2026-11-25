@echo off
cd /d "%~dp0"
set CONTROL_BIND=0.0.0.0
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 server.py
) else (
  python server.py
)
pause
