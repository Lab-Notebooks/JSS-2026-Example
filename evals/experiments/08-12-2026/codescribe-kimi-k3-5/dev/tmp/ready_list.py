import csv, os

rows = list(csv.DictReader(open('dev/tmp/assets/roadmap_metrics.tsv'), delimiter='\t'))
ready = []
for r in rows:
    if r['deps'] == '0' and r['blind'] == '0':
        cpp = os.path.join('software/mcfm/src', r['rel']).rsplit('.', 1)[0] + '.cpp'
        if not os.path.exists(cpp):
            ready.append(r)
print('total rows', len(rows), 'ready (deps=0, blind=0, no cpp)', len(ready))
from collections import Counter
print(Counter(r['top'] for r in ready))
print('--- sample per folder ---')
seen = {}
for r in ready:
    seen.setdefault(r['top'], []).append(r)
for top, lst in sorted(seen.items()):
    print('##', top, len(lst))
    for r in lst[:6]:
        print('  ', r['rel'], 'fanin=' + r['fanin'], 'bench=' + (r['bench'] or '-'))
