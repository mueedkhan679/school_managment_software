@echo off
cd /d "%~dp0student_portal_app"
del /q "%~dp0build_final_output.txt" 2>nul
for /L %%i in (1,1,5) do (
  echo === ATTEMPT %%i === >> "%~dp0build_final_output.txt"
  call flutter build apk --debug >> "%~dp0build_final_output.txt" 2>&1
  if not errorlevel 1 (
    echo BUILD_EXIT:0 >> "%~dp0build_final_output.txt"
    exit /b 0
  )
  ping -n 6 127.0.0.1 >nul
)
echo BUILD_EXIT:1 >> "%~dp0build_final_output.txt"
