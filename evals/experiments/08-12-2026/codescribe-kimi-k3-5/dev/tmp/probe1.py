import csv, os, glob

rows = list(csv.DictReader(open('dev/tmp/assets/roadmap_metrics.tsv'), delimiter='\t'))
names = ['fmt', 'fzip', 'storecsz', 'ampqqb_qqb', 'Bdiff', 'msq_z2jetx']
print('=== roadmap rows for group-1 files ===')
for r in rows:
    base = r['rel'].rsplit('/', 1)[-1].rsplit('.', 1)[0]
    if base in names:
        print(dict(r))
print('=== module headers ===')
for h in ['masses_mod', 'constants_mod', 'mmsq_cs_mod', 'loopI2_generic', 'scale_mod',
          'scalarselect_mod', 'nf_mod', 'ewcharge_mod', 'zcouple_mod', 'zcouple_cms_mod']:
    hits = glob.glob('software/mcfm/src/**/' + h + '.*pp', recursive=True)
    print(h, hits)
print('=== callees ===')
for c in ['aqqb_zbb_new', 'atreez', 'lnrat', 'I3m', 'cplx2', 'loopI2', 'spinoru']:
    hits = glob.glob('software/mcfm/src/**/' + c + '.*', recursive=True)
    print(c, hits)
print('=== _fi shims present ===')
fis = glob.glob('software/mcfm/src/**/*_fi*', recursive=True)
for f in fis[:30]:
    print(f)
print('count', len(fis))
