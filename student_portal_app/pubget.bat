@echo off
cd /d "%~dp0"
C:\flutter\flutter\bin\flutter.bat pub get > _pubget_log.txt 2>&1
echo PUBGET_EXIT=%ERRORLEVEL% >> _pubget_log.txt
