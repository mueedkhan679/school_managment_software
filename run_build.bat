@echo off
cd /d "%~dp0student_portal_app"
call flutter build apk --debug >> ..\build_output.txt 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> ..\build_output.txt
