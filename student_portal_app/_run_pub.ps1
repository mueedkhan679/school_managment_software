Start-Process -FilePath 'C:\flutter\flutter\bin\flutter.bat' `
  -ArgumentList 'pub', 'get' `
  -WorkingDirectory 'c:\Users\ytmoi\Desktop\school_project\student_portal_app' `
  -WindowStyle Hidden `
  -RedirectStandardOutput 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\pub_get_log.txt' `
  -RedirectStandardError 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\pub_get_err.txt'
Write-Output 'pub get launched'
