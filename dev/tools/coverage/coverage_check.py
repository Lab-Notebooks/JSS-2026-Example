"""Coverage check (stage 1) — decides VERIFIED vs TRANSLATED for one rewritten MCFM file.

  source environment.sh
  python3 coverage_check.py <target.cpp> -- <process args>
  e.g. python3 coverage_check.py software/mcfm/src/Z/qqb_z.cpp -- u u~ e- e+

A passing test is necessary but not sufficient: fixed inputs might never reach your
routine. This proves a test actually ran the file, and ALWAYS restores the file and
leaves a clean build, even on failure. Steps: snapshot -> build+test (baseline) ->
scale the marked output by FACTOR -> build+test (probed) -> restore+rebuild -> compare.
Numbers changed = COVERED (VERIFIED-eligible); identical = NOT COVERED (mark TRANSLATED).

Mark the one statement that writes the main output, e.g.
    msq(i, j) = ampsq;   // @coverage-probe
Needs a NORMAL shell (so the CodeScribe loop can't run it) and $MCFM_HOME.
Overrides: FACTOR (1.5), FC/CC/CXX (gfortran/gcc/g++). Exit: 0 covered, 1 not, 2 usage/setup.
"""
import os, re, sys, shutil, tempfile, subprocess

FACTOR = os.environ.get("FACTOR", "1.5")


def die(msg):
    print(f"error: {msg}", file=sys.stderr); sys.exit(2)


def build(bin, mcfm):
    if not os.path.isfile(bin + "/CMakeCache.txt"):
        subprocess.run(["cmake",
                        "-DCMAKE_Fortran_COMPILER=" + os.environ.get("FC", "gfortran"),
                        "-DCMAKE_C_COMPILER=" + os.environ.get("CC", "gcc"),
                        "-DCMAKE_CXX_COMPILER=" + os.environ.get("CXX", "g++"),
                        "-DCMAKE_INSTALL_PREFIX=" + mcfm + "/install",
                        "-S", mcfm, "-B", bin], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["make", "-C", bin, "install"], check=True, stdout=subprocess.DEVNULL)


def run_test(bin, process):
    return subprocess.run([bin + "/test", "-b", *process], capture_output=True, text=True).stdout


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        die("usage: coverage_check.py <target.cpp> -- <process args>")
    target = argv[0]
    if len(argv) < 2 or argv[1] != "--":
        die("put the test process after --, e.g. -- u u~ e- e+")
    process = argv[2:]
    if not process:
        die("no test process given after --")

    mcfm = os.environ.get("MCFM_HOME") or die("set MCFM_HOME first (source environment.sh)")
    if not os.path.isfile(target):
        die("target file not found: " + target)
    text = open(target).read()
    if text.count("@coverage-probe") == 0:
        die(f"no '// @coverage-probe' marker in {target} — mark the statement that writes the main output")
    if text.count("@coverage-probe") != 1:
        die(f"found more than one '@coverage-probe' marker in {target} — keep exactly one")

    bin = mcfm + "/Bin"
    if not os.path.isdir(bin):
        die(f"no MCFM build dir at {bin} — build MCFM once first (jobrunner submit tests/mcfm)")

    snapshot = tempfile.mktemp()
    shutil.copy(target, snapshot)
    print(f"== coverage check: {target} ==\nprocess : {' '.join(process)}\nfactor  : {FACTOR}")
    try:
        print("-- baseline build + test --")
        build(bin, mcfm)
        baseline = run_test(bin, process)

        print(f"-- scaling the marked output by {FACTOR} --")
        # On the marked line only: lhs = rhs;  // @coverage-probe -> lhs = (rhs) * FACTOR;  // ...
        scaled = re.sub(r"(=\s*)(.*);(\s*//.*@coverage-probe.*)$",
                        rf"\1(\2) * {FACTOR};\3", text, flags=re.M)
        open(target, "w").write(scaled)
        if f"* {FACTOR};" not in scaled:
            die("could not scale the marked line — is it a plain 'lhs = rhs;   // @coverage-probe' statement?")

        print("-- probed build + test --")
        build(bin, mcfm)
        probed = run_test(bin, process)
    finally:
        shutil.copy(snapshot, target)
        os.remove(snapshot)
        try:
            build(bin, mcfm)  # rebuild from restored source so the tree is left correct
        except subprocess.CalledProcessError:
            print("warning: final rebuild after restore failed — rebuild MCFM before trusting the binary", file=sys.stderr)

    print()
    if baseline == probed:
        print("RESULT: NOT COVERED — the numbers did not change, so the test never ran this file.")
        print("  Mark it TRANSLATED. Check again after a routine that calls it is rewritten.")
        return 1
    print("RESULT: COVERED — the numbers changed, so the test exercised this file.")
    print("  If the restored build now PASSES its match, this file is VERIFIED-eligible.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
