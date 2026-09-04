@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0student_portal_app\android"
rem Deterministic artifact seeding: the Gradle JVM cannot reach remote repos
rem on this network, but curl demonstrably can. Seeds the exact artifacts the
rem google-services 4.4.2 plugin graph needs into android/local-maven.
set BASE_A=https://maven.aliyun.com/repository/public
set BASE_B=https://repo1.maven.org/maven2
set BASE_C=https://dl.google.com/dl/android/maven2
set BASE_D=https://maven.aliyun.com/repository/google
set FAIL=0
set OK=0
set SKIP=0
if exist seed_failures.txt del /q seed_failures.txt
for /f "usebackq delims=" %%L in ("%~dp0seed_list.txt") do (
  if exist "local-maven\%%L" (
    set /a SKIP+=1
  ) else (
    call :fetch "%%L"
  )
)
echo SEED_DONE OK=!OK! SKIP=!SKIP! FAIL=!FAIL!
if exist seed_failures.txt type seed_failures.txt
exit /b 0

:fetch
set P=%~1
curl -fsS -m 25 --create-dirs -o "local-maven\%P%" "%BASE_A%/%P%" && goto got
curl -fsS -m 25 --create-dirs -o "local-maven\%P%" "%BASE_B%/%P%" && goto got
curl -fsS -m 25 --create-dirs -o "local-maven\%P%" "%BASE_C%/%P%" && goto got
curl -fsS -m 25 --create-dirs -o "local-maven\%P%" "%BASE_D%/%P%" && goto got
echo %P% >> seed_failures.txt
set /a FAIL+=1
goto :eof
:got
set /a OK+=1
goto :eof
