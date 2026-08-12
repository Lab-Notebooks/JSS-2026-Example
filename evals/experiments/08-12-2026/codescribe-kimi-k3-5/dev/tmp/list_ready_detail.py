import csv, sys, os

top = sys.argv[1]
with open('dev/tmp/assets/roadmap_metrics.tsv') as f:
    r = csv.DictReader(f, delimiter='\t')
    for row in r:
        if row['deps'] == '0' and row['blind'] == '0' and row['top'] == top:
            print(row['rel'], 'fanin=' + row['fanin'], 'bench=' + row['bench'])
