$ErrorActionPreference = 'Stop'
$base = 'c:\Users\ytmoi\Desktop\school_project\student_portal_app'

function Dump([string]$file, [int]$from, [int]$to, [string]$out) {
  $lines = Get-Content (Join-Path $base $file)
  $end = [Math]::Min($to, $lines.Count)
  $sb = New-Object System.Text.StringBuilder
  for ($i = $from; $i -le $end; $i++) {
    [void]$sb.AppendLine(('{0,4}: {1}' -f $i, $lines[$i - 1]))
  }
  [System.IO.File]::WriteAllText((Join-Path $base $out), $sb.ToString())
}

Dump 'lib\views\dashboard_view.dart' 76 262 '_cur_dash.txt'
Dump 'lib\views\attendance_view.dart' 87 120 '_cur_att.txt'
Dump 'lib\views\digital_id_card_view.dart' 1 80 '_cur_did.txt'
Dump 'lib\views\dashboard_view.dart' 136 204 '_cur_dash2.txt'
Dump 'lib\views\fee_view.dart' 1 140 '_cur_fee1.txt'
Dump 'lib\views\fee_view.dart' 196 420 '_cur_fee2.txt'
Dump 'lib\widgets\modern_loader.dart' 1 120 '_cur_ml.txt'
Dump 'lib\widgets\shimmer_placeholders.dart' 1 150 '_cur_sh.txt'
Dump 'lib\models\student_profile.dart' 1 120 '_cur_prof.txt'
Dump 'pubspec.yaml' 1 60 '_cur_pub.txt'
Write-Output 'done'
