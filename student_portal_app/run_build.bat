@echo off
cd /d C:\Users\ytmoi\Desktop\school_project\student_portal_app
echo [%date% %time%] ============ STEP 1/3: FLUTTER CLEAN ============
call flutter clean
echo [%date% %time%] clean exit code: %errorlevel%
echo [%date% %time%] ============ STEP 2/3: FLUTTER PUB GET ============
call flutter pub get
echo [%date% %time%] pub get exit code: %errorlevel%
echo [%date% %time%] ============ STEP 3/3: FLUTTER BUILD APK RELEASE ============
call flutter build apk --release
echo [%date% %time%] ============ BUILD EXIT CODE: %errorlevel% ============
echo DONE > build_done.flag