@echo off
cd /d "%~dp0"
"C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe" manage.py check > "%~dp0backend_verify_output.txt" 2>&1
echo CHECK_EXIT:%ERRORLEVEL% >> "%~dp0backend_verify_output.txt"
"C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe" manage.py test apps.api >> "%~dp0backend_verify_output.txt" 2>&1
echo TEST_EXIT:%ERRORLEVEL% >> "%~dp0backend_verify_output.txt"
