import io

base = r'c:\Users\ytmoi\Desktop\school_project\student_portal_app'
ranges = [
    (r'_r_login.txt', 96, 172),
    (r'_r_fee.txt', 215, 245),
    (r'_r_fee.txt', 285, 315),
    (r'_r_dash.txt', 240, 296),
    (r'_r_did.txt', 1, 45),
]
out = []
for fname, lo, hi in ranges:
    with io.open(base + '\\' + fname, encoding='utf-8') as fh:
        lines = fh.readlines()
    out.append('===== %s [%d-%d] =====' % (fname, lo, hi))
    for i in range(lo - 1, min(hi, len(lines))):
        out.append('%d: %s' % (i + 1, lines[i].rstrip('\n')))

with io.open(base + r'\_dump_ctx.txt', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(out))
print('ok')
