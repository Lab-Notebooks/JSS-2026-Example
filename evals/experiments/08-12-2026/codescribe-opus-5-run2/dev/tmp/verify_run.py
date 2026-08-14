"""Run `dev/workflow.py verify` with MCFM_HOME set (bash tool cannot source environment.sh).

usage: python3 dev/tmp/verify_run.py <target.cpp> -- <process args>
"""
import os
import subprocess
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env = dict(os.environ)
env["MCFM_HOME"] = os.path.join(root, "software", "mcfm")

cmd = [sys.executable, os.path.join(root, "dev", "workflow.py"), "verify"] + sys.argv[1:]
proc = subprocess.run(cmd, cwd=root, env=env)
sys.exit(proc.returncode)
