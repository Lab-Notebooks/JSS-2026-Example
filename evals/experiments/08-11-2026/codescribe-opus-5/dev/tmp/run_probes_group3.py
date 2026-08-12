#!/usr/bin/env python3
"""Run the coverage probe for each W2jet-helpers-3 file, one after another."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MCFM_HOME", str(ROOT / "software" / "mcfm"))
sys.path.insert(0, str(ROOT / "dev" / "tools" / "coverage"))

import coverage_check  # noqa: E402

FILES = [
    "software/mcfm/src/W2jet/a6treeg.cpp",
    "software/mcfm/src/W2jet/vvg.cpp",
    "software/mcfm/src/W2jet/subqcd.cpp",
    "software/mcfm/src/W2jet/Acalc.cpp",
    "software/mcfm/src/W2jet/LRcalc.cpp",
]
PROCESS = ["u", "d~", "ve", "e+", "g", "g"]

results = {}
for f in FILES:
    rc = coverage_check.main([f, "--"] + PROCESS)
    results[f] = rc

print("== probe summary ==")
for f, rc in results.items():
    print(f, "exit", rc, "COVERED" if rc == 0 else "NOT COVERED/FAILED")
