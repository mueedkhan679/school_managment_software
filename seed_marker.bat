@echo off
cd /d "%~dp0student_portal_app\android\local-maven"
set "B=https://plugins.gradle.org/m2/com/google/gms/google-services"
mkdir "com\google\gms\google-services\com.google.gms.google-services.gradle.plugin\4.4.2" 2>nul
curl -fsS -m 30 --retry 3 -o "com\google\gms\google-services\com.google.gms.google-services.gradle.plugin\4.4.2\com.google.gms.google-services.gradle.plugin-4.4.2.pom" "%B%/com.google.gms.google-services.gradle.plugin/4.4.2/com.google.gms.google-services.gradle.plugin-4.4.2.pom" && echo MARKER_OK || echo MARKER_FAIL
curl -fsS -m 90 --retry 3 -o "com\google\gms\google-services\4.4.2\google-services-4.4.2.module" "%B%/4.4.2/google-services-4.4.2.module" && echo MODULE_OK || echo MODULE_FAIL
cd /d "%~dp0student_portal_app\android"
dir /s /a:-d local-maven > "%~dp0maven_inventory.txt" 2>&1
echo INVENTORY_WRITTEN
