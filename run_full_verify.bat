@echo off
cd /d "%~dp0"
echo === CHECK === > verify_output.txt 2>&1
"C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe" manage.py check >> verify_output.txt 2>&1
echo CHECK_EXIT:%ERRORLEVEL% >> verify_output.txt
echo === TESTS === >> verify_output.txt 2>&1
"C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe" manage.py test apps.api >> verify_output.txt 2>&1
echo TEST_EXIT:%ERRORLEVEL% >> verify_output.txt
cd student_portal_app
echo === ANALYZE === >> ..\verify_output.txt 2>&1
call flutter analyze >> ..\verify_output.txt 2>&1
echo ANALYZE_EXIT:%ERRORLEVEL% >> ..\verify_output.txt
echo === BUILD === >> ..\verify_output.txt 2>&1
call flutter build apk --debug >> ..\verify_output.txt 2>&1
echo BUILD_EXIT:%ERRORLEVEL% >> ..\verify_output.txt
