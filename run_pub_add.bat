@echo off
cd /d "%~dp0student_portal_app"
call flutter pub add firebase_core firebase_messaging > pub_add_output.txt 2>&1
echo PUBADD_EXIT:%ERRORLEVEL% >> pub_add_output.txt
