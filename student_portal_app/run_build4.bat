@echo off
cd /d C:\Users\ytmoi\Desktop\school_project\student_portal_app
echo [%date% %time%] Starting flutter build apk --release (ONLINE)...
echo [%date% %time%] ====== START ====== > build_log4.txt
call flutter pub get >> build_log4.txt 2>&1
echo [%date% %time%] pub get exit: %errorlevel% >> build_log4.txt
call flutter build apk --release >> build_log4.txt 2>&1
echo [%date% %time%] build exit: %errorlevel% >> build_log4.txt
echo DONE4 > build_done4.flag