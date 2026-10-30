@echo off
cd /d "%~dp0"
echo ============================================
echo   ZhiYu Tutor - starting
echo   backend 8000 / frontend 5173
echo   browser will open automatically
echo ============================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
    echo.
    echo Start failed. Check the error above.
)
echo.
echo You can close this window. Services run in two other windows.
pause
