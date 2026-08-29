$workdir = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'C:\flutter\flutter\bin\flutter.bat pub get > pub_get_log.txt 2>&1' -WorkingDirectory $workdir -WindowStyle Hidden
Start-Sleep -Seconds 2
Write-Output "launcher-exit"
