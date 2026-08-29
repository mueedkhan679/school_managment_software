$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'

function Dump-Range($file, $start, $end, $out) {
  $i = 0
  Get-Content $file | ForEach-Object {
    $i++
    if ($i -ge $start -and $i -le $end) { ("{0}: {1}" -f $i, $_) }
  } | Out-File $out -Encoding utf8
}

Dump-Range "$base\lib\views\login_view.dart" 103 165 "$base\_dump_login_mid.txt"
Dump-Range "$base\lib\views\fee_view.dart" 89 248 "$base\_dump_fee_mid.txt"
Copy-Item "$base\lib\views\digital_id_card_view.dart" "$base\_dump_did.txt" -Force
Copy-Item "$base\lib\views\attendance_view.dart" "$base\_dump_att.txt" -Force
Copy-Item "$base\lib\views\qr_scan_view.dart" "$base\_dump_qr.txt" -Force
Write-Output "dumps done"
