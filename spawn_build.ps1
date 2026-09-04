# Spawn the APK build detached from this console via WMI (runs under the WMI provider host).
# Returns the ProcessId so we can poll for it specifically.
$cmd = 'cmd.exe /c C:\Users\ytmoi\Desktop\school_project\run_apk_build.bat'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
"ReturnValue: $($result.ReturnValue)"
"ProcessId: $($result.ProcessId)"
if ($result.ReturnValue -ne 0) {
  "Failed to spawn. Error code $($result.ReturnValue)"
  exit 1
}