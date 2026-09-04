@echo off
cd /d "%~dp0student_portal_app"
call flutter doctor -v > ..\jdk_info.txt 2>&1
echo DONE >> ..\jdk_info.txt
