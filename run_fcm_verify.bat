@echo off
cd /d "%~dp0student_portal_app"
echo === PUB GET === > "%~dp0fcm_verify_output.txt"
call flutter pub get >> "%~dp0fcm_verify_output.txt" 2>&1
echo PUBGET_EXIT:%ERRORLEVEL% >> "%~dp0fcm_verify_output.txt"
echo === ANALYZE === >> "%~dp0fcm_verify_output.txt"
call flutter analyze >> "%~dp0fcm_verify_output.txt" 2>&1
echo FLUTTER_EXIT:%ERRORLEVEL% >> "%~dp0fcm_verify_output.txt"
echo === BUILD DEBUG APK (validates google-services wiring) === >> "%~dp0fcm_verify_output.txt"
call flutter build apk --debug >> "%~dp0fcm_verify_output.txt" 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> "%~dp0fcm_verify_output.txt"
