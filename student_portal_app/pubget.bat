@echo off
cd /d c:\Users\ytmoi\Desktop\school_project\student_portal_app
C:\flutter\flutter\bin\flutter.bat pub get > _pubget_log.txt 2>&1
echo EXITCODE=%ERRORLEVEL% >> _pubget_log.txt
