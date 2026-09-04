$t1 = @{}
Get-Process -Name dart,dartvm,java -ErrorAction SilentlyContinue | ForEach-Object { $t1[$_.Id] = $_.CPU }
Start-Sleep -Seconds 6
"PID;PROC;CPU_T0;CPU_T1;DELTA"
Get-Process -Name dart,dartvm,java -ErrorAction SilentlyContinue | ForEach-Object {
  $t0 = $t1[$_.Id]
  if ($null -eq $t0) { $t0 = 0 }
  $d = [Math]::Round($_.CPU - $t0, 2)
  "{0};{1};{2};{3};{4}" -f $_.Id, $_.ProcessName, $t0, [Math]::Round($_.CPU,2), $d
}