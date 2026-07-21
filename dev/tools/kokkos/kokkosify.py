"""Kokkos tool — mechanical C++ -> Kokkos pre-pass, plus a host validation harness.

  python3 kokkosify.py <input.cpp> [-o draft.h] [-r report.md]   ('-' = stdout)
  python3 kokkosify.py validate <validator.cpp> [extra g++ args...]

kokkosify: applies the safe subset of the stage-2 rewriting rules to a stage-1 C++
file and emits a draft kernel body (NOT compilable as-is) plus a blocker report.
Anything it cannot decide safely it flags with a KOKKOSIFY-TODO. Rewrites:
std::complex<double> -> C ; std:: math -> Kokkos:: ; KOKKOS_INLINE_FUNCTION on
file-scope functions ; #include lines dropped. Flags only: QCDLoop, STL/heap/IO,
module-global reads, FArray declarations, wrappers.

validate: compile+run a standalone validator that links the original MCFM C++
(libmcfm) alongside the ported kernels, compiled host-side via kokkos_host_shim/.
Overrides: MCFM_DIR, KERNELS_DIR, SHIM_DIR, CXX, CXXFLAGS (or MCFM_HOME/PEPPER_HOME).
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, shlex
from pathlib import Path

HERE = Path(__file__).resolve().parent

MATH = ["sqrt", "cbrt", "exp", "log", "log10", "pow", "sin", "cos", "tan",
        "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "fabs", "abs", "conj"]

BLOCKERS = [
    (re.compile(r"\bloopI[1-4]\b|\bqli\w*\b"), "QCDLoop -> analytic closed form (Spec's loop-integral rule)"),
    (re.compile(r"\bstd::(vector|map|string)\b"), "STL -> fixed-size local / not allowed on device"),
    (re.compile(r"\bstd::c(out|err)\b|\bprintf\s*\("), "host I/O -> remove"),
    (re.compile(r"\bthrow\b"), "exception -> Kokkos::abort() or restructure"),
    (re.compile(r"\bnew\b|\bdelete\b"), "heap -> fixed-size local array"),
]
RET = r"(?:void|double|int|bool|C)"


def kokkosify(src, name):
    report = {"blockers": [], "globals": set(), "farrays": [], "wrappers": [], "annotated": []}
    for n, line in enumerate(src.splitlines(), 1):
        for pat, why in BLOCKERS:
            if pat.search(line):
                report["blockers"].append((n, line.strip()[:80], why))
        for m in re.finditer(r"\b(\w+_mod)::(\w+)", line):
            report["globals"].add(f"{m.group(1)}::{m.group(2)}")
        for m in re.finditer(r"\bFArray([1-4])D\s*<[^>]*>\s*&?\s*(\w+)", line):
            report["farrays"].append((n, m.group(2), int(m.group(1))))
        if re.search(r"\b\w+_wrapper\s*\(", line):
            report["wrappers"].append((n, line.strip()[:80]))

    text = re.sub(r"std::complex\s*<\s*double\s*>", "C", src)
    for fn in MATH:
        text = re.sub(rf"\bstd::{fn}\b", f"Kokkos::{fn}", text)

    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#include"):
            continue
        if re.match(r"using\s+namespace\s+\w+_mod\s*;", s):
            out.append(f"// KOKKOSIFY-TODO(params): was `{s}` -> move reads into *_Params")
            continue
        if re.search(r"\bFArray[1-4]D\b", line):
            out.append("// KOKKOSIFY-TODO(array): use a fixed-size local array instead of FArray:")
            out.append("// " + s)
            continue
        m = re.match(rf"^({RET})\s+(\w+)\s*\(", line)
        if m and not s.endswith(";"):
            fn = m.group(2)
            if fn.endswith("_wrapper") or fn == "main":
                out.append("// KOKKOSIFY-TODO(drop): stage-1 C-ABI artifact, not device code:")
                out.append("// " + s)
                continue
            out.append("KOKKOS_INLINE_FUNCTION")
            report["annotated"].append(fn)
        out.append(line)

    banner = (f"// MACHINE-GENERATED DRAFT (kokkosify.py) from {name} -- NOT compilable as-is.\n"
              "// Resolve every KOKKOSIFY-TODO; follow the stage-2 Spec and Plan to finish.\n"
              '#pragma once\n#include "../math.h"\n')
    return banner + "\n" + "\n".join(out) + "\n", report


def format_report(r, name):
    L = [f"# kokkosify report -- {name}", "", "## Blockers (must be resolved; Spec's rewriting + loop-integral rules)"]
    L += [f"- L{n}: `{code}` -- {why}" for n, code, why in r["blockers"]] or ["- none"]
    L += ["", "## Candidate *_Params fields (module globals read)"]
    L += [f"- `{g}`" for g in sorted(r["globals"])] or ["- none"]
    L += ["", "## FArray declarations -> fixed-size local arrays (agent sizes them)"]
    L += [f"- L{n}: `{nm}` rank {rk}" for n, nm, rk in r["farrays"]] or ["- none"]
    L += ["", "## Dropped C-ABI wrappers"]
    L += [f"- L{n}: `{code}`" for n, code in r["wrappers"]] or ["- none"]
    L += ["", "## Functions annotated KOKKOS_INLINE_FUNCTION", "- " + (", ".join(r["annotated"]) or "none"), ""]
    return "\n".join(L)


def run_kokkosify(argv):
    ap = argparse.ArgumentParser(prog="kokkosify.py", description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("-r", "--report", default=None)
    args = ap.parse_args(argv)

    p = Path(args.input)
    draft, report = kokkosify(p.read_text(), p.name)
    rep = format_report(report, p.name)

    out = args.out or str(p.with_suffix("")) + ".kokkosified.h"
    repout = args.report or str(p.with_suffix("")) + ".kokkosify-report.md"
    sys.stdout.write(draft) if out == "-" else (Path(out).write_text(draft), print(f"draft:  {out}"))
    sys.stdout.write(rep) if repout == "-" else (Path(repout).write_text(rep), print(f"report: {repout}"))


def validate(argv):
    """Compile and run a standalone validator."""
    if not argv:
        sys.exit("usage: kokkosify.py validate <validator.cpp> [extra g++ args...]")
    validator, extra = argv[0], argv[1:]

    root = os.environ.get("PROJECT_HOME") or str(HERE.parent.parent.parent)
    mcfm = os.environ.get("MCFM_DIR") or os.environ.get("MCFM_HOME") or (root + "/software/mcfm")
    if os.path.isdir(mcfm + "/install/include"):
        inc, lib = mcfm + "/install/include", mcfm + "/install/lib"
    elif os.path.isdir(mcfm + "/include"):
        inc, lib = mcfm + "/include", mcfm + "/lib"
    else:
        sys.exit("error: set MCFM_DIR to the mcfminterface dir (with install/include and install/lib)")

    kernels = os.environ.get("KERNELS_DIR")
    if not kernels and os.environ.get("PEPPER_HOME"):
        kernels = os.environ["PEPPER_HOME"] + "/src/mcfm_analytics"
    if not kernels or not os.path.isdir(kernels):
        sys.exit("error: set KERNELS_DIR to .../src/mcfm_analytics (or export PEPPER_HOME)")

    cxx = os.environ.get("CXX") or next((c for c in ("g++-15", "g++", "c++") if shutil.which(c)), None)
    if not cxx:
        sys.exit("error: no C++ compiler found; set CXX")
    cxxflags = shlex.split(os.environ.get("CXXFLAGS", "-O3 -march=native"))

    shim = os.environ.get("SHIM_DIR", str(HERE))
    with tempfile.TemporaryDirectory() as build:
        # Mirror the kernels' relative includes: kernels under <build>/mcfm_analytics/
        # so their `../math.h` resolves to the shim headers copied into <build>/.
        shutil.copytree(kernels, os.path.join(build, "mcfm_analytics"))
        for h in ("math.h", "event_handle.h", "kernel_macros.h"):
            shutil.copy(os.path.join(shim, "kokkos_host_shim", h), os.path.join(build, h))

        binpath = os.path.join(build, "validator")
        print(f"compiler : {cxx} {' '.join(cxxflags)}\nMCFM     : {inc}\nkernels  : {kernels}")
        cmd = [cxx, "-std=c++17", *cxxflags, "-I", inc, "-I", build, validator,
               "-L", lib, "-lmcfm", "-Wl,-rpath," + lib, *extra, "-o", binpath]
        if subprocess.run(cmd).returncode:
            sys.exit(1)
        sys.exit(subprocess.run([binpath]).returncode)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate(sys.argv[2:])
    else:
        run_kokkosify(sys.argv[1:])
