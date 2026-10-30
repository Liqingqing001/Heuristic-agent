@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.env" copy "backend\.env.example" "backend\.env" >nul 2>&1

if not exist "frontend\node_modules" (
    echo Installing frontend dependencies, please wait...
    pushd frontend
    call npm install
    popd
)

echo Starting backend (8000) and frontend (5173)...
start "zhiyu-backend" /min /d "%~dp0backend" cmd /c "py -m uvicorn app.main:app --port 8000"
start "zhiyu-frontend" /min /d "%~dp0frontend" cmd /c "npm run dev"

echo Waiting for services...
set READY=0
for /l %%i in (1,1,90) do (
    curl -s -o nul --max-time 2 http://localhost:8000/api/health
    if not errorlevel 1 (
        curl -s -o nul --max-time 2 http://localhost:5173/
        if not errorlevel 1 (
            set READY=1
            goto :ready
        )
    )
    timeout /t 1 >nul
)

:ready
if "%READY%"=="0" (
    echo.
    echo Services did not start in time. Check the two minimized windows.
    pause
    exit /b 1
)

set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
    start "" "%EDGE%" --app=http://localhost:5173/ --user-data-dir="%TEMP%\zhiyu-demo-profile" --window-size=1440,960 --no-first-run
) else (
    start "" "http://localhost:5173/"
)

echo.
echo Ready: http://localhost:5173/
echo Demo teacher: demo_teacher / demo123456
echo Demo student: demo_student / demo123456
echo Fill your DeepSeek key in "Model Settings" before chatting.
echo To stop everything, run stop.bat.
timeout /t 3 >nul
exit /b 0
