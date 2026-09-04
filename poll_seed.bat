@echo off
cd /d "%~dp0"
findstr /c:SEED_DONE seed_run_log.txt >nul 2>&1
if not errorlevel 1 goto done
ping -n 22 127.0.0.1 >nul
findstr /c:SEED_DONE seed_run_log.txt >nul 2>&1
if not errorlevel 1 goto done
echo STILL_RUNNING
powershell -NoProfile -Command "(Get-ChildItem -Recurse -File 'student_portal_app\android\local-maven' | Measure-Object).Count"
exit /b 0
:done
echo SEED_COMPLETE
findstr /c:SEED_DONE seed_run_log.txt
echo ===FAILURES===
type student_portal_app\android\seed_failures.txt 2>nul
echo ===COUNT===
powershell -NoProfile -Command "(Get-ChildItem -Recurse -File 'student_portal_app\android\local-maven' | Measure-Object).Count"
