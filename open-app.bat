@echo off
rem Open the app in an Edge app window with a dedicated profile.
rem Kept in a .bat so "start" fully detaches the GUI process.
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" (
    start "" "http://localhost:5173/"
    exit /b 0
)
start "" "%EDGE%" --app=http://localhost:5173/ --user-data-dir="%TEMP%\zhiyu-demo-profile" --window-size=1440,960 --no-first-run
