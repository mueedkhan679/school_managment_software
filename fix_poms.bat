@echo off
cd /d "%~dp0student_portal_app\android"
powershell -NoProfile -Command "$files = @('local-maven\com\google\gms\google-services\4.4.2\google-services-4.4.2.pom','local-maven\com\google\android\gms\strict-version-matcher-plugin\1.2.4\strict-version-matcher-plugin-1.2.4.pom'); foreach ($f in $files) { $c = Get-Content $f | Where-Object { $_ -notmatch 'do_not_remove' -and $_ -notmatch 'richer model' -and $_ -notmatch 'is to indicate' -and $_ -notmatch 'should prefer consuming' }; Set-Content -Path $f -Value $c -Encoding UTF8 }"
echo STRIP_EXIT:%ERRORLEVEL%
powershell -NoProfile -Command "Get-ChildItem -Recurse -File local-maven | ForEach-Object { $rel = $_.FullName.Substring((Get-Location).Path.Length + 1); Write-Output ($rel + '|' + $_.Length) }" > "%~dp0maven_files.txt" 2>&1
echo AUDIT_EXIT:%ERRORLEVEL%
