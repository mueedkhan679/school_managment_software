$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
$out = "$base\_gaps_dump.txt"
$targets = @(
  @{ f = "$base\_tmp_fee.txt"; s = 90; e = 250 },
  @{ f = "$base\lib\views\qr_scan_view.dart"; s = 1; e = 228 }
)
Remove-Item $out -ErrorAction SilentlyContinue
foreach ($t in $targets) {
  $i = 0
  $label = Split-Path $t.f -Leaf
  ("===== {0} {1}-{2} =====" -f $label, $t.s, $t.e) | Out-File $out -Append -Encoding utf8
  Get-Content $t.f | ForEach-Object {
    $i++
    if ($i -ge $t.s -and $i -le $t.e) { ("{0}: {1}" -f $i, $_) }
  } | Out-File $out -Append -Encoding utf8
}
Write-Output "done"
