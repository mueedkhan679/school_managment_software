$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
$files = @(
  @{ src = "$base\lib\views\fee_view.dart"; out = "$base\_dump_fee.txt" },
  @{ src = "$base\lib\views\digital_id_card_view.dart"; out = "$base\_dump_did.txt" },
  @{ src = "$base\lib\views\attendance_view.dart"; out = "$base\_dump_att.txt" },
  @{ src = "$base\lib\views\qr_scan_view.dart"; out = "$base\_dump_qr.txt" },
  @{ src = "$base\lib\views\dashboard_view.dart"; out = "$base\_dump_dash.txt" },
  @{ src = "$base\lib\views\teacher_dashboard_view.dart"; out = "$base\_dump_td.txt" },
  @{ src = "$base\lib\views\main_scaffold_view.dart"; out = "$base\_dump_ms.txt" }
)
foreach ($f in $files) {
  $i = 0
  Get-Content $f.src | ForEach-Object {
    $i++
    ("{0}: {1}" -f $i, $_)
  } | Out-File $f.out -Encoding utf8
}
Write-Output "dumps done"
