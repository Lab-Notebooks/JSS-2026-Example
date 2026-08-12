import os
import subprocess
import sys

# usage: python3 dev/tmp/run_cmd.py <tag> <cmd...>
tag = sys.argv[1]
cmd = sys.argv[2:]
env = dict(os.environ)
root = os.getcwd()
env.setdefault("MCFM_HOME", os.path.join(root, "software/mcfm"))
r = subprocess.run(cmd, capture_output=True, text=True, env=env)
open(f"dev/tmp/{tag}_stdout.txt", "w").write(r.stdout or "")
open(f"dev/tmp/{tag}_stderr.txt", "w").write(r.stderr or "")
print("exit", r.returncode)
print("=== STDOUT (tail) ===")
print((r.stdout or "")[-4000:])
print("=== STDERR (tail) ===")
print((r.stderr or "")[-4000:])
