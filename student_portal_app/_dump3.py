import io

base = r'c:\Users\ytmoi\Desktop\school_project\student_portal_app'

jobs = {
    '_dump_a.txt': [
        (r'lib\views\attendance_view.dart', 1, 210),
    ],
    '_dump_b.txt': [
        (r'lib\views\digital_id_card_view.dart', 1, 109),
        (r'lib\views\digital_id_card_view.dart', 242, 336),
        (r'lib\views\fee_view.dart', 155, 250),
    ],
}

for outfile, ranges in jobs.items():
    out = []
    for fname, lo, hi in ranges:
        path = base + '\\' + fname
        with io.open(path, encoding='utf-8') as fh:
            lines = fh.readlines()
        out.append('===== %s [%d-%d] =====' % (fname, lo, hi))
        for i in range(lo - 1, min(hi, len(lines))):
            out.append('%d: %s' % (i + 1, lines[i].rstrip('\n')))
    with io.open(base + '\\' + outfile, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out))
print('done')
