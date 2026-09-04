$procs = Get-CimInstance Win32_Process -Filter "Name='java.exe' OR Name='dart.exe' OR Name='cmd.exe'"
foreach ($p in $procs) {
    $cl = $p.CommandLine
    if ($cl -and $cl.Length -gt 220) { $cl = $cl.Substring(0, 220) + "...TRUNC" }
    Write-Output ("PID=" + $p.ProcessId + " CREATED=" + $p.CreationDate + " CMD=" + $cl)
    Write-Output "----"
}
