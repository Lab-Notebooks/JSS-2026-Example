import os, subprocess, sys

root = os.getcwd()
os.environ.setdefault("MCFM_HOME", os.path.join(root, "software/mcfm"))
files = sys.argv[1:]
process = ["u", "u~", "e-", "e+", "g", "g"]
for f in files:
    print("=" * 70)
    print("VERIFY", f)
    r = subprocess.run([sys.executable, "dev/workflow.py", "verify", f, "--", *process],
                       capture_output=True, text=True)
    print(r.stdout[-3000:])
    print("stderr:", r.stderr[-1500:])
    print("exit", r.returncode)
