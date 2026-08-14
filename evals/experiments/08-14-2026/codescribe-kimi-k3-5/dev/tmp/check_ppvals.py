import re

def parse_f90(path):
    text = open(path).read()
    m = re.search(r'reshape\s*\(\(/(.*?)/\)\s*&\s*,\s*\(/\s*9\s*,\s*9\s*,\s*9\s*,\s*9\s*/\)\s*\)',
                  text, re.S)
    vals = [v.strip() for v in m.group(1).replace('&', '').replace('\n', ' ').split(',')]
    vals = [int(v) for v in vals if v]
    return vals

def parse_cpp(path):
    text = open(path).read()
    m = re.search(r'int pp_init\[[^\]]*\]\s*=\s*\{(.*?)\};', text, re.S)
    vals = [v.strip() for v in m.group(1).replace('\n', ' ').split(',')]
    vals = [int(v) for v in vals if v]
    return vals

ok = True
for mod in ['pp_mod', 'ppwp2j_mod']:
    f = parse_f90(f'software/mcfm/src/Mods/deprecated/{mod}.f90')
    c = parse_cpp(f'software/mcfm/src/Mods/{mod}.cpp')
    if f == c and len(c) == 6561:
        nz = sum(1 for v in c if v != 0)
        print(f"{mod}: MATCH, 6561 values, {nz} nonzero")
    else:
        ok = False
        print(f"{mod}: MISMATCH len f={len(f)} c={len(c)}")
        for i, (a, b) in enumerate(zip(f, c)):
            if a != b:
                print(f"  first diff at {i}: f90={a} cpp={b}")
                break

# also confirm Fortran shims/headers exist for both, types_mod.hpp exists
import os
for p in ['software/mcfm/src/Mods/types_mod.hpp',
          'software/mcfm/src/Mods/pp_mod.hpp',
          'software/mcfm/src/Mods/ppwp2j_mod.hpp',
          'software/mcfm/src/Mods/pp_mod.cpp',
          'software/mcfm/src/Mods/ppwp2j_mod.cpp',
          'software/mcfm/src/Inc/deprecated/tri123x4x56coeffs.f']:
    print(p, 'exists' if os.path.exists(p) else 'MISSING')
print('ppmax.f present in Inc:', os.path.exists('software/mcfm/src/Inc/ppmax.f'))
