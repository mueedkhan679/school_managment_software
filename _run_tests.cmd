@echo off
cd /d "C:\Users\ytmoi\Desktop\school_project"
set _PY="C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe"
set _MGMT="C:\Users\ytmoi\Desktop\school_project\manage.py"
set _OUT="C:\Users\ytmoi\Desktop\school_project\_test_out.txt"
set _ERR="C:\Users\ytmoi\Desktop\school_project\_test_err.txt"
%_PY% %_MGMT% test "apps.accounts" > %_OUT% 2> %_ERR%
echo ----DONE---- >> %_OUT%
