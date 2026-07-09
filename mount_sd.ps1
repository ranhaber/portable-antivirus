$log = "$env:USERPROFILE\wsl_mount_log.txt"
"Attempting mount at $(Get-Date)" | Out-File $log

# Take the SD card offline in Windows so WSL/Hyper-V can passthrough
"--- Setting Disk 1 offline ---" | Add-Content $log
try {
    Set-Disk -Number 1 -IsOffline $true -ErrorAction Stop
    "Disk 1 set offline OK" | Add-Content $log
} catch {
    "Set offline failed: $_" | Add-Content $log
}
Start-Sleep -Seconds 2

"--- wsl --mount --bare ---" | Add-Content $log
wsl --mount \\.\PHYSICALDRIVE1 --bare *>> $log
$code = $LASTEXITCODE
"EXITCODE=$code" | Add-Content $log

if ($code -ne 0) {
    "--- mount failed, bringing disk back online ---" | Add-Content $log
    try {
        Set-Disk -Number 1 -IsOffline $false -ErrorAction Stop
        "Disk 1 back online OK" | Add-Content $log
    } catch {
        "Set online failed: $_" | Add-Content $log
    }
}
