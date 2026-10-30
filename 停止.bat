@echo off
cd /d "%~dp0"
echo Stopping ZhiYu Tutor...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
timeout /t 2 >nul
