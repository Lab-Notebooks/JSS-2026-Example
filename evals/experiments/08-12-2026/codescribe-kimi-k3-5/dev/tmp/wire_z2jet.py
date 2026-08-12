"""Loop-4 wiring for Group 1 (Z2jet helpers) — idempotent.

1. Move the six original .f files into software/mcfm/src/Z2jet/deprecated/
   (git mv when tracked, plain move otherwise).
2. Rewrite software/mcfm/src/Z2jet/CMakeLists.txt swapping each .f entry for
   the generated .cpp + _fi.f90 pair.
"""
import os
import shutil
import subprocess

ZD = "software/mcfm/src/Z2jet"
BASES = ["fmt", "fzip", "storecsz", "ampqqb_qqb", "Bdiff", "msq_z2jetx"]

depdir = os.path.join(ZD, "deprecated")
os.makedirs(depdir, exist_ok=True)

# --- step 1: move .f files into deprecated/ (skip if already moved)
for b in BASES:
    src = os.path.join(ZD, b + ".f")
    dst = os.path.join(depdir, b + ".f")
    if not os.path.exists(src):
        print(f"already moved: {b}.f")
        continue
    r = subprocess.run(["git", "ls-files", "--error-unmatch", src],
                       capture_output=True, text=True)
    if r.returncode == 0:
        m = subprocess.run(["git", "mv", src, dst], capture_output=True, text=True)
        if m.returncode != 0:
            print(f"git mv failed for {b}.f: {m.stderr.strip()}; falling back to shutil.move")
            shutil.move(src, dst)
        else:
            print(f"git mv {b}.f -> deprecated/")
    else:
        shutil.move(src, dst)
        print(f"shutil.move {b}.f -> deprecated/ (untracked)")

# --- step 2: rewrite CMakeLists.txt
lines = open(os.path.join(ZD, "CMakeLists.txt")).read().splitlines()
repl = {
    "ampqqb_qqb.f": ["ampqqb_qqb.cpp", "ampqqb_qqb_fi.f90"],
    "Bdiff.f": ["Bdiff.cpp", "Bdiff_fi.f90"],
    "fmt.f": ["fmt.cpp", "fmt_fi.f90"],
    "fzip.f": ["fzip.cpp", "fzip_fi.f90"],
    "msq_z2jetx.f": ["msq_z2jetx.cpp", "msq_z2jetx_fi.f90"],
    "storecsz.f": ["storecsz.cpp", "storecsz_fi.f90"],
}
out = []
changed = 0
for ln in lines:
    key = ln.strip()
    # exact filename line (with optional indent)
    if key in repl and ln == key:
        out.extend(repl[key])
        changed += 1
        print(f"CMakeLists: {key} -> {' '.join(repl[key])}")
    else:
        if key in repl:
            print(f"WARNING: unexpected CMakeLists line format for {key!r}: {ln!r}")
        out.append(ln)
if changed != 6:
    print(f"WARNING: expected 6 replacements, made {changed}")
open(os.path.join(ZD, "CMakeLists.txt"), "w").write("\n".join(out) + "\n")
print("done")
