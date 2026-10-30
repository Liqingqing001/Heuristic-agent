@echo off
cd /d "%~dp0"
echo Stopping ZhiYu Tutor (backend 8000 / frontend 5173)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
echo.
pause
