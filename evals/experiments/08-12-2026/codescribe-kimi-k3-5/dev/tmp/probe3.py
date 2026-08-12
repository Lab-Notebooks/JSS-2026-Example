import re, glob, os

print("=== where is Bdiff called ===")
for f in glob.glob("software/mcfm/src/**/*.f", recursive=True) + glob.glob("software/mcfm/src/**/*.f90", recursive=True):
    try:
        txt = open(f, errors='replace').read()
    except Exception:
        continue
    for m in re.finditer(r"\bBdiff\s*\(", txt):
        # skip the definition itself
        if "function Bdiff" in txt:
            print(f, "(definition+maybe call)")
        else:
            print(f)
        break

print("=== mmsq_cs dimension declaration in Fortran ===")
for f in glob.glob("software/mcfm/src/**/mmsq*", recursive=True):
    print(f)
    for i, line in enumerate(open(f, errors='replace'), 1):
        if "mmsq_cs" in line and ("(" in line or "dimension" in line.lower()):
            print("   ", i, line.rstrip())

print("=== qqb_z2jetx_new.f head (mmsq_cs usage) ===")
txt = open("software/mcfm/src/Z2jet/qqb_z2jetx_new.f", errors="replace").read()
for i, line in enumerate(txt.splitlines(), 1):
    if "storecsz" in line or "msq_qq" in line or "ampqqb_qqb" in line or "mmsq_cs" in line:
        print("   ", i, line.rstrip())

print("=== nf_mod.hpp / ewcharge_mod.hpp / zcouple headers ===")
for f in ["software/mcfm/src/Mods/nf_mod.hpp", "software/mcfm/src/Mods/ewcharge_mod.hpp",
          "software/mcfm/src/Mods/zcouple_mod.hpp", "software/mcfm/src/Mods/zcouple_cms_mod.hpp",
          "software/mcfm/src/Mods/masses_mod.hpp"]:
    print("--", f, "exists:", os.path.exists(f))
