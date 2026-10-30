<#
    Stop everything started by start.ps1:
    - the Edge app window (dedicated profile)
    - backend / frontend processes and whatever still holds 8000 / 5173

    NOTE: keep this file ASCII-only (Windows PowerShell 5.1 reads .ps1 as ANSI).
#>
$ErrorActionPreference = "SilentlyContinue"

$killed = @()
$profile = Join-Path $env:TEMP "zhiyu-demo-profile"

# 1) Close the dedicated Edge app window
$edges = Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*zhiyu-demo-profile*" }
foreach ($edge in $edges) {
    taskkill /F /T /PID $edge.ProcessId 2>&1 | Out-Null
    $killed += $edge.ProcessId
}

# 2) Backend / frontend processes of this project
$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*uvicorn app.main:app*" -or
        ($_.CommandLine -like "*vite*" -and $_.CommandLine -like "*Heuristic-agent*") -or
        ($_.CommandLine -like "*npm*run dev*" -and $_.CommandLine -like "*Heuristic-agent*")
    )
}
foreach ($process in $targets) {
    Stop-Process -Id $process.ProcessId -Force
    $killed += $process.ProcessId
}

# 3) Whatever still holds the ports (retry: workers may inherit sockets)
for ($round = 0; $round -lt 5; $round++) {
    Start-Sleep -Milliseconds 500
    foreach ($port in 8000, 5173) {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen
        foreach ($connection in $connections) {
            Stop-Process -Id $connection.OwningProcess -Force
            $killed += $connection.OwningProcess
        }
    }
}

$unique = $killed | Select-Object -Unique
if ($unique.Count -gt 0) {
    Write-Host ("Stopped: " + ($unique -join ", "))
} else {
    Write-Host "Nothing was running."
}
Write-Host "Done - all windows and services are closed."
