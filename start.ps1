<#
    One-click launcher: backend on 8000 + frontend on 5173.

    Usage:
        .\start.ps1             # start (dependencies already installed)
        .\start.ps1 -Install    # install dependencies first

    NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads .ps1 as ANSI,
    so non-ASCII characters without a BOM break parsing.
#>
param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "== ZhiYu Tutor == starting" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $backend ".env"))) {
    Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env")
    Write-Host "Created backend/.env from .env.example" -ForegroundColor Yellow
}

if ($Install) {
    Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
    py -m pip install -r (Join-Path $backend "requirements.txt")
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontend
    npm install
    Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "frontend/node_modules missing, installing..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$backend'; py -m uvicorn app.main:app --port 8000"
)

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$frontend'; npm run dev"
)

Write-Host "Waiting for backend..." -ForegroundColor Cyan
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) { break }
    } catch { }
}

Start-Process "http://localhost:5173/"
Write-Host ""
Write-Host "Opened http://localhost:5173/" -ForegroundColor Green
Write-Host "Demo teacher: demo_teacher / demo123456" -ForegroundColor Gray
Write-Host "Demo student: demo_student / demo123456" -ForegroundColor Gray
Write-Host "Fill your own DeepSeek API key in 'Model Settings' before chatting." -ForegroundColor Yellow
