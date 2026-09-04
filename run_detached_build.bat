@echo off
cd /d c:\Users\ytmoi\Desktop\school_project\student_portal_app
flutter build apk --debug > c:\Users\ytmoi\Desktop\school_project\build_output.txt 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> c:\Users\ytmoi\Desktop\school_project\build_output.txt
