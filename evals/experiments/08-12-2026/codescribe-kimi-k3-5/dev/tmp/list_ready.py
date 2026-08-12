import csv, sys, os

rows = []
with open('dev/tmp/assets/roadmap_metrics.tsv') as f:
    r = csv.DictReader(f, delimiter='\t')
    for row in r:
        if row['deps'] == '0' and row['blind'] == '0':
            rows.append(row)

def hascpp(rel):
    base = os.path.splitext(os.path.basename(rel))[0]
    d = os.path.join('software/mcfm/src', os.path.dirname(rel))
    return os.path.exists(os.path.join(d, base + '.cpp'))

if len(sys.argv) > 1:
    topfilter = sys.argv[1]
    rows = [x for x in rows if x['top'] == topfilter]

print('count_ready:', len(rows))
from collections import Counter
c = Counter(x['top'] for x in rows)
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(k, v)
