@echo off
cd /d c:\Users\ytmoi\Desktop\school_project\student_portal_app
echo === FCM BUILD STARTED %date% %time% === > c:\Users\ytmoi\Desktop\school_project\apk_build_output.txt
flutter build apk --debug >> c:\Users\ytmoi\Desktop\school_project\apk_build_output.txt 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> c:\Users\ytmoi\Desktop\school_project\apk_build_output.txt
echo === FCM BUILD FINISHED %date% %time% === >> c:\Users\ytmoi\Desktop\school_project\apk_build_output.txt

