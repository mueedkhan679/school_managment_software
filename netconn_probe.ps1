"=== DAEMON PIDS ==="
Get-Process -Name java -ErrorAction SilentlyContinue | Select-Object Id, @{N='CPU';E={[Math]::Round($_.CPU,2)}}, StartTime | Format-Table -AutoSize

"=== TCP FOR ALL JAVA ==="
$javaPids = (Get-Process -Name java -ErrorAction SilentlyContinue).Id
foreach ($p in $javaPids) {
  Get-NetTCPConnection -OwningProcess $p -ErrorAction SilentlyContinue |
    Select-Object @{N='PID';E={$p}}, State, RemoteAddress, RemotePort |
    Format-Table -AutoSize
}

"=== NEWEST GRADLE LOG TAIL ==="
$log = Get-ChildItem -Path "$env:USERPROFILE\.gradle\daemon" -Recurse -Filter *.out.log -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($log) {
  "LOG: $($log.FullName)  LASTWRITE: $($log.LastWriteTime)"
  Get-Content $log.FullName -Tail 8
}