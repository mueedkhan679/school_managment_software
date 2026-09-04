$log = Get-ChildItem -Path "$env:USERPROFILE\.gradle\daemon" -Recurse -Filter *.log -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($log) {
  "LOG: $($log.FullName)"
  "LAST WRITE: $($log.LastWriteTime)"
  Get-Content $log.FullName -Tail 20
} else {
  "NO GRADLE LOGS FOUND"
}