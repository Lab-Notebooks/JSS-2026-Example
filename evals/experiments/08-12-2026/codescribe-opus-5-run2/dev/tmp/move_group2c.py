"""Move translated W2jet Fortran originals into deprecated/ (loop 4: fpm, fsl)."""
import os
import shutil

base = os.path.join("software", "mcfm", "src", "W2jet")
dep = os.path.join(base, "deprecated")
os.makedirs(dep, exist_ok=True)
for name in ["fpm.f", "fsl.f"]:
    src = os.path.join(base, name)
    if os.path.exists(src):
        shutil.move(src, os.path.join(dep, name))
        print("moved", src)
    else:
        print("missing", src)
print(sorted(os.listdir(dep)))
