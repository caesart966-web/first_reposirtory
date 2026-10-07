# Join value lines that were split by embedded newlines (LibreDWG MTEXT output)
import sys, re
src, dst = sys.argv[1], sys.argv[2]
raw = open(src, 'rb').read().decode('utf-8', errors='replace')
lines = raw.replace('\r\n', '\n').split('\n')
out = []
i = 0
gc = re.compile(r'^\s*-?\d{1,4}$')
fixed = 0
while i < len(lines) - 1:
    code = lines[i]
    if not gc.match(code):
        # stray line: append to previous value
        out[-1] = out[-1] + '\\P' + code
        fixed += 1
        i += 1
        continue
    out.append(code); out.append(lines[i+1]); i += 2
open(dst, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('fixed', fixed)
