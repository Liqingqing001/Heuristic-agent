<#
    一键启动：后端 8000 + 前端 5173，并自动打开浏览器。

    用法（在项目根目录）：
        .\start.ps1             # 直接启动（依赖已装好时）
        .\start.ps1 -Install    # 先安装依赖再启动
#>
param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "== 智育助教 == 启动中" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $backend ".env"))) {
    Copy-Item (Join-Path $backend ".env.example") (Join-Path $backend ".env")
    Write-Host "已从 .env.example 创建 backend/.env（可留空，使用者在网页里填自己的 key）" -ForegroundColor Yellow
}

if ($Install) {
    Write-Host "安装后端依赖…" -ForegroundColor Cyan
    py -m pip install -r (Join-Path $backend "requirements.txt")
    Write-Host "安装前端依赖…" -ForegroundColor Cyan
    Push-Location $frontend
    npm install
    Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "缺少 frontend/node_modules，正在安装…" -ForegroundColor Yellow
    Push-Location $frontend
    npm install
    Pop-Location
}

Write-Host "启动后端 http://localhost:8000 …" -ForegroundColor Green
Start-Process pwsh -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$backend'; py -m uvicorn app.main:app --reload --port 8000"
)

Write-Host "启动前端 http://localhost:5173 …" -ForegroundColor Green
Start-Process pwsh -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$frontend'; npm run dev"
)

Write-Host "等待服务就绪…" -ForegroundColor Cyan
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) { break }
    } catch { }
}

Start-Process "http://localhost:5173/"
Write-Host ""
Write-Host "已打开 http://localhost:5173/" -ForegroundColor Green
Write-Host "演示账号：demo_teacher / demo123456    教师" -ForegroundColor Gray
Write-Host "          demo_student / demo123456    学生" -ForegroundColor Gray
Write-Host "首次使用请在右上角「模型设置」填写自己的 DeepSeek Key。" -ForegroundColor Yellow
