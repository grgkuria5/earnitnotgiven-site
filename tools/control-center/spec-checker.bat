@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:8765/#spec
where py >nul 2>&1 && py -3 server.py || python server.py
