@echo off
cd /d C:\Users\ytmoi\Desktop\school_project\student_portal_app
echo [%date% %time%] Starting OFF-LINE flutter build apk --release...
call flutter build apk --release > build_log2.txt 2>&1
echo [%date% %time%] BUILD EXIT CODE: %errorlevel% >> build_log2.txt
echo DONE2 > build_done2.flag