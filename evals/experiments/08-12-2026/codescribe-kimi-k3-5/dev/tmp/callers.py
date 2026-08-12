"""Find Fortran callers of the six translated Z2jet symbols across src/."""
import glob
import sys

syms = sys.argv[1:] or ["fmt", "fzip", "storecsz", "Bdiff", "ampqqb_qqb",
                        "msq_z2jetx", "msq_qq", "msq_qqb"]
skip_dirs = ("deprecated",)
for f in sorted(glob.glob("software/mcfm/src/**/*.f*", recursive=True)):
    if any(s in f for s in skip_dirs):
        continue
    try:
        lines = open(f, errors="ignore").read().splitlines()
    except OSError:
        continue
    for i, ln in enumerate(lines, 1):
        low = ln.lower()
        for sym in syms:
            if sym.lower() in low:
                print(f"{f}:{i}:{ln.strip()[:110]}")
                break
