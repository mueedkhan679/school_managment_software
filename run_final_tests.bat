@echo off
cd /d "%~dp0"
"C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe" manage.py test apps.api -v 1 > "%~dp0tests_final_output.txt" 2>&1
echo TEST_EXIT:%ERRORLEVEL% >> "%~dp0tests_final_output.txt"
