#!/usr/bin/env python3
"""Move converted W2jet Fortran originals into W2jet/deprecated/."""
import shutil
from pathlib import Path

SRC = Path("software/mcfm/src/W2jet")
DEST = SRC / "deprecated"
DEST.mkdir(exist_ok=True)

for name in ["a6treeg.f", "Acalc.f", "LRcalc.f", "subqcd.f", "vvg.f"]:
    src = SRC / name
    if src.exists():
        shutil.move(str(src), str(DEST / name))
        print("moved", name)
    else:
        print("missing", name)
