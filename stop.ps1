<#
    Stop the dev servers started by start.ps1.

    NOTE: keep this file ASCII-only (Windows PowerShell 5.1 reads .ps1 as ANSI).
#>
$ErrorActionPreference = "SilentlyContinue"

$killed = @()

# 1) processes whose command line clearly belongs to this project
$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*uvicorn app.main:app*" -or
        ($_.CommandLine -like "*vite*" -and $_.CommandLine -like "*Heuristic-agent*")
    )
}
foreach ($process in $targets) {
    Stop-Process -Id $process.ProcessId -Force
    $killed += $process.ProcessId
}

# 2) whichever process still holds the ports; retry a few times because uvicorn
#    may spawn a worker that inherits the socket a moment later.
for ($round = 0; $round -lt 4; $round++) {
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
    Write-Host ("Stopped processes: " + ($unique -join ", "))
} else {
    Write-Host "No running service found."
}
Write-Host "Done."
Start-Sleep -Seconds 1
