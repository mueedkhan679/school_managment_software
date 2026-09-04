"=== BUILD PROCESSES ==="
Get-CimInstance Win32_Process -Filter "Name='dart.exe' OR Name='dartvm.exe' OR Name='cmd.exe'" |
  Where-Object { $_.CommandLine -match 'build apk|run_apk_build' } |
  Select-Object ProcessId, Name, CommandLine |
  Format-List

"=== TASK RESULT ==="
schtasks /query /tn FCMBuild /v /fo LIST 2>$null | Out-String | ForEach-Object { $_ -split "`r`n" } | Where-Object { $_ -match "Last Result|Status" }