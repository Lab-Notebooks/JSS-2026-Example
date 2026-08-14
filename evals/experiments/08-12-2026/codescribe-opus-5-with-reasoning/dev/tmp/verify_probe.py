import os, sys

os.environ.setdefault("MCFM_HOME", os.path.abspath("software/mcfm"))
sys.path.insert(0, os.path.abspath("dev/tools/coverage"))

import coverage_check

sys.exit(coverage_check.main(sys.argv[1:]))
