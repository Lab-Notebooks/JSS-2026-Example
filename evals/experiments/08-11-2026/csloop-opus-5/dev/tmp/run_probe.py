#!/usr/bin/env python3
"""Helper: run dev/tools/coverage/coverage_check.py with MCFM_HOME set.

Usage: python3 dev/tmp/run_probe.py <target.cpp> -- <process args>
"""
import os
import sys
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MCFM_HOME", str(ROOT / "software" / "mcfm"))
sys.path.insert(0, str(ROOT / "dev" / "tools" / "coverage"))

import coverage_check  # noqa: E402

sys.exit(coverage_check.main(sys.argv[1:]))
