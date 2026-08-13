import os
import subprocess
import sys

os.environ["MCFM_HOME"] = "/home/user/JSS-2026-Example/software/mcfm"

targets = ["vv", "fpm", "fpp", "fsl", "fvf"]
for t in targets:
    target = f"software/mcfm/src/W2jet/{t}.cpp"
    print(f"\n===== verifying {target} =====", flush=True)
    rc = subprocess.run(
        [sys.executable, "dev/tools/coverage/coverage_check.py", target, "--", "u", "d~", "ve", "e+", "g", "g"]
    ).returncode
    print(f"===== {t}: exit {rc} =====", flush=True)
