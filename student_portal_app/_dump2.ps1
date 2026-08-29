$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\lib\views'
function Dump($file, $from, $to, $out) {
  $i = 0
  Get-Content (Join-Path $base $file) | ForEach-Object {
    $i++
    if ($i -ge $from -and $i -le $to) { ("{0}: {1}" -f $i, $_) }
  } | Out-File $out -Encoding utf8
}
Dump 'login_view.dart' 96 170 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\_lv.txt'
Dump 'fee_view.dart' 88 235 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\_fv.txt'
Dump 'dashboard_view.dart' 78 100 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\_dv.txt'
Write-Output 'done'
