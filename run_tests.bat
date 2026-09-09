@echo off
cd /d "%~dp0"
set PY=C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe
"%PY%" manage.py check > "%~dp0verify_output.txt" 2>&1
echo CHECK_EXIT:%ERRORLEVEL% >> "%~dp0verify_output.txt"
"%PY%" manage.py test apps.api -v 1 >> "%~dp0verify_output.txt" 2>&1
echo TEST_EXIT:%ERRORLEVEL% >> "%~dp0verify_output.txt"
\
