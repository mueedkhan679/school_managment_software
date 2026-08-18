@echo off
cd /d c:\Users\ytmoi\Desktop\school_project
py download_wheels.py > dl.log 2>&1
echo SCRIPT_EXIT %errorlevel% >> dl.log
