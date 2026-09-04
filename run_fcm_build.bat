@echo off
cd /d "%~dp0student_portal_app"
echo === BUILD DEBUG APK (validates google-services wiring) === > "%~dp0fcm_build_output.txt"
call flutter build apk --debug >> "%~dp0fcm_build_output.txt" 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> "%~dp0fcm_build_output.txt"
