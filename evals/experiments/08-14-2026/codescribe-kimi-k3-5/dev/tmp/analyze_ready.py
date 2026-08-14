import csv
from collections import Counter, defaultdict

rows = []
with open('dev/tmp/assets/roadmap_metrics.tsv') as f:
    r = csv.DictReader(f, delimiter='\t')
    for x in r:
        rows.append(x)

ready = [x for x in rows if x['deps'] == '0' and x['blind'] == '0']
c = Counter(x['top'] for x in ready)
print("ready counts per top-level folder:")
for top, n in sorted(c.items()):
    print(f"  {top}: {n}")

print()
by_top = defaultdict(list)
for x in ready:
    by_top[x['top']].append(x)

# Show ready files in infra folders first (safe seeds)
for top in ['Mods', 'Need', 'Inc', 'Procdep']:
    if top in by_top:
        print(f"== {top} ready files ==")
        for x in by_top[top][:30]:
            print(f"  {x['rel']}  fanin={x['fanin']} bench={x['bench']!r}")
