$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
$out = Join-Path $base '_dump_out.txt'
Remove-Item $out -ErrorAction SilentlyContinue

function Dump-Range($file, $from, $to) {
  $i = 0
  Add-Content -Path $out -Value "===== $file [$from-$to] ====="
  Get-Content (Join-Path $base $file) | ForEach-Object {
    $i++
    if ($i -ge $from -and $i -le $to) { Add-Content -Path $out -Value ("{0}: {1}" -f $i, $_) }
  }
}

Dump-Range 'lib\views\login_view.dart' 99 170
Dump-Range 'lib\views\fee_view.dart' 88 250
Dump-Range 'lib\views\digital_id_card_view.dart' 109 242
Dump-Range 'lib\views\attendance_view.dart' 1 210
Dump-Range 'lib\views\qr_scan_view.dart' 1 230
Write-Output "done"
