"""Run `dev/workflow.py verify` for several targets with MCFM_HOME set.

usage: python3 dev/tmp/verify_all.py <process words...> --files <a.cpp> <b.cpp> ...
"""
import os
import subprocess
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env = dict(os.environ)
env["MCFM_HOME"] = os.path.join(root, "software", "mcfm")

args = sys.argv[1:]
i = args.index("--files")
process = args[:i]
files = args[i + 1:]

results = {}
for f in files:
    cmd = [sys.executable, os.path.join(root, "dev", "workflow.py"), "verify", f, "--"] + process
    proc = subprocess.run(cmd, cwd=root, env=env)
    results[f] = proc.returncode

print("=== SUMMARY ===")
for f, rc in results.items():
    print(f, "->", "COVERED" if rc == 0 else ("NOT COVERED" if rc == 1 else f"ERROR({rc})"))
