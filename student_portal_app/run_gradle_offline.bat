@echo off
set JAVA_HOME=C:\PROGRA~1\Android\ANDROI~1\jbr
set PATH=%JAVA_HOME%\bin;%PATH%
cd /d C:\Users\ytmoi\Desktop\school_project\student_portal_app\android
echo [%date% %time%] Starting DIRECT ONLINE GRADLE assembleRelease...
call gradlew.bat :app:assembleRelease --no-daemon --console=plain --stacktrace -Pflutter.buildMode=release > C:\Users\ytmoi\Desktop\school_project\student_portal_app\build_log3.txt 2>&1
echo [%date% %time%] GRADLE EXIT CODE: %errorlevel% >> C:\Users\ytmoi\Desktop\school_project\student_portal_app\build_log3.txt
echo DONE3 > C:\Users\ytmoi\Desktop\school_project\student_portal_app\build_done3.flag