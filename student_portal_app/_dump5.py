import io

base = r'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
out = []

for fname, lo, hi in [
    (r'lib\views\attendance_view.dart', 1, 206),
    (r'lib\views\qr_scan_view.dart', 1, 112),
    (r'lib\views\digital_id_card_view.dart', 130, 242),
    (r'lib\views\fee_view.dart', 160, 250),
]:
    path = base + '\\' + fname
    with io.open(path, encoding='utf-8') as fh:
        lines = fh.readlines()
    out.append('===== %s [%d-%d] =====' % (fname, lo, hi))
    for i in range(lo - 1, min(hi, len(lines))):
        out.append('%d: %s' % (i + 1, lines[i].rstrip('\n')))

with io.open(base + r'\_dump_out3.txt', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(out))
print('done')
