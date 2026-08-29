$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\lib\views'
$out  = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app\_dash_dump.txt'
$ranges = @(
  @{ f = 'fee_view.dart'; a = 88; b = 250 },
  @{ f = 'attendance_view.dart'; a = 85; b = 122 },
  @{ f = 'digital_id_card_view.dart'; a = 110; b = 230 },
  @{ f = 'login_view.dart'; a = 100; b = 166 }
)
$lines = foreach ($r in $ranges) {
  $path = Join-Path $base $r.f
  $i = 0
  "===== $($r.f) $($r.a)-$($r.b) ====="
  Get-Content $path | ForEach-Object {
    $i++
    if ($i -ge $r.a -and $i -le $r.b) { ("{0}: {1}" -f $i, $_) }
  }
}
$lines | Out-File $out -Encoding utf8
Write-Output 'dumped'
