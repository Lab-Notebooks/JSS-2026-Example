import re, glob, os

def grep(pat, path):
    out = []
    rx = re.compile(pat)
    try:
        with open(path, errors='replace') as fh:
            for i, line in enumerate(fh, 1):
                if rx.search(line):
                    out.append(f"{i}: {line.rstrip()}")
    except FileNotFoundError:
        out.append("FILE NOT FOUND")
    return out

print("=== aqqb_zbb_new references ===")
for f in ["software/mcfm/src/Z2jet/atreez.f", "software/mcfm/src/W2jet/aqqb_zbb.f"]:
    print("--", f)
    for l in grep(r"aqqb_zbb_new|atreez", f)[:20]:
        print("   ", l)

print("=== who calls the 6 group-1 symbols ===")
syms = ["fmt", "fzip", "storecsz", "Bdiff", "ampqqb_qqb", "msq_qq", "msq_qqb"]
for f in sorted(glob.glob("software/mcfm/src/Z2jet/*.f")) + sorted(glob.glob("software/mcfm/src/Z2jet/*.f90")):
    hits = []
    with open(f, errors='replace') as fh:
        txt = fh.read()
    for s in syms:
        for m in re.finditer(r"\b" + re.escape(s) + r"\s*\(", txt):
            hits.append(s)
    print(f, sorted(set(hits)))

print("=== mmsq_cs include file ===")
for f in glob.glob("software/mcfm/src/Inc/mmsq*"):
    print(f)
    print(open(f, errors='replace').read())

print("=== masses_mod mt decl ===")
for l in grep(r"\bmt\b", "software/mcfm/src/Mods/masses_mod.hpp")[:10]:
    print("   ", l)

print("=== cplx2 / i3m in Need ===")
for f in glob.glob("software/mcfm/src/Need/*.f90"):
    base = os.path.basename(f)
    if base in ("cplx.f90", "i3m.f90", "i2m.f90", "i4m.f90"):
        print(f)

print("=== Loop.hpp ===")
print(open("software/mcfm/src/Inc/Loop.hpp", errors='replace').read() if os.path.exists("software/mcfm/src/Inc/Loop.hpp") else "missing")
for f in glob.glob("software/mcfm/src/**/Loop.hpp", recursive=True):
    print("found:", f)
    print(open(f, errors='replace').read())
