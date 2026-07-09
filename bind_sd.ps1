$log = "$env:USERPROFILE\usbipd_log.txt"
$usbipd = "C:\Program Files\usbipd-win\usbipd.exe"
"usbipd bind/attach at $(Get-Date)" | Out-File $log

"--- bind 8-3 ---" | Add-Content $log
& $usbipd bind --busid 8-3 *>> $log
"bind EXIT=$LASTEXITCODE" | Add-Content $log

Start-Sleep -Seconds 1

"--- attach 8-3 to wsl ---" | Add-Content $log
& $usbipd attach --wsl --busid 8-3 *>> $log
"attach EXIT=$LASTEXITCODE" | Add-Content $log

Start-Sleep -Seconds 1
"--- state ---" | Add-Content $log
& $usbipd list *>> $log
