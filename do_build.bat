@echo off
cd /d c:\Users\ytmoi\Desktop\school_project\student_portal_app
echo PHASE_PUBGET > build_log.txt
flutter pub get >> build_log.txt 2>&1
echo PHASE_BUILD >> build_log.txt
flutter build apk --debug >> build_log.txt 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> build_log.txt
