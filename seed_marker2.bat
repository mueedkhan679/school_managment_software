@echo off
cd /d "%~dp0student_portal_app\android\local-maven"
setlocal enabledelayedexpansion
set "MD=com\google\gms\google-services\com.google.gms.google-services.gradle.plugin\4.4.2\com.google.gms.google-services.gradle.plugin-4.4.2.pom"
set "MO=com\google\gms\google-services\4.4.2\google-services-4.4.2.module"
type nul > "!MD!"
type nul > "!MO!"

curl -fsS -m 45 -o "!MD!" "https://maven.aliyun.com/repository/gradle-plugin/com/google/gms/google-services/com.google.gms.google-services.gradle.plugin/4.4.2/com.google.gms.google-services.gradle.plugin-4.4.2.pom" 2>nul
for %%Z in ("!MD!") do set S=%%~zZ
if !S! EQU 0 curl -fsS -m 45 -o "!MD!" "https://dl.google.com/dl/android/maven2/com/google/gms/google-services/com.google.gms.google-services.gradle.plugin/4.4.2/com.google.gms.google-services.gradle.plugin-4.4.2.pom" 2>nul
for %%Z in ("!MD!") do set S=%%~zZ
if !S! EQU 0 curl -fsS -m 45 -o "!MD!" "https://plugins.gradle.org/m2/com/google/gms/google-services/com.google.gms.google-services.gradle.plugin/4.4.2/com.google.gms.google-services.gradle.plugin-4.4.2.pom" 2>nul
for %%Z in ("!MD!") do set S=%%~zZ
echo MARKER_SIZE=!S!

curl -fsS -m 60 -o "!MO!" "https://maven.aliyun.com/repository/google/com/google/gms/google-services/4.4.2/google-services-4.4.2.module" 2>nul
for %%Z in ("!MO!") do set S=%%~zZ
if !S! EQU 0 curl -fsS -m 60 -o "!MO!" "https://dl.google.com/dl/android/maven2/com/google/gms/google-services/4.4.2/google-services-4.4.2.module" 2>nul
for %%Z in ("!MO!") do set S=%%~zZ
if !S! EQU 0 curl -fsS -m 60 -o "!MO!" "https://plugins.gradle.org/m2/com/google/gms/google-services/4.4.2/google-services-4.4.2.module" 2>nul
for %%Z in ("!MO!") do set S=%%~zZ
echo MODULE_SIZE=!S!
endlocal
