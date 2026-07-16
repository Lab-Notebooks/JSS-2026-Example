#!/usr/bin/env python3
"""Kokkosify tool — a deterministic pre-pass for a C++ -> Kokkos kernel draft.

Applies the mechanical subset of the stage-2 Spec (§3) to a stage-1 C++ file and
emits two things: a draft kernel body (NOT compilable as-is) and a blocker report.
Zero tokens at run time; anything it cannot decide safely it flags with a
KOKKOSIFY-TODO rather than guessing. The Author agent resolves every TODO and
finishes the port, with the §4 validation ladder as the safety net.

Rewrites (safe): std::complex<double> -> C ; std:: math -> Kokkos:: ;
KOKKOS_INLINE_FUNCTION on file-scope functions ; #include lines -> ../math.h.
Flags only (never rewritten): QCDLoop calls, STL/heap/IO, module-global reads
(-> Params fields), FArray declarations (-> fixed-size local arrays), wrappers.

Usage: kokkosify.py input.cpp [-o draft.h] [-r report.md]   ('-' = stdout)
"""
import argparse, re, sys
from pathlib import Path

MATH = ["sqrt", "cbrt", "exp", "log", "log10", "pow", "sin", "cos", "tan",
        "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "fabs", "abs", "conj"]

BLOCKERS = [
    (re.compile(r"\bloopI[1-4]\b|\bqli\w*\b"), "QCDLoop -> analytic closed form (Spec §5)"),
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
              "// Resolve every KOKKOSIFY-TODO; follow the stage-2 Spec §2-4 to finish.\n"
              '#pragma once\n#include "../math.h"\n')
    return banner + "\n" + "\n".join(out) + "\n", report


def format_report(r, name):
    L = [f"# kokkosify report -- {name}", "", "## Blockers (must be resolved; Spec §3/§5)"]
    L += [f"- L{n}: `{code}` -- {why}" for n, code, why in r["blockers"]] or ["- none"]
    L += ["", "## Candidate *_Params fields (module globals read)"]
    L += [f"- `{g}`" for g in sorted(r["globals"])] or ["- none"]
    L += ["", "## FArray declarations -> fixed-size local arrays (agent sizes them)"]
    L += [f"- L{n}: `{nm}` rank {rk}" for n, nm, rk in r["farrays"]] or ["- none"]
    L += ["", "## Dropped C-ABI wrappers"]
    L += [f"- L{n}: `{code}`" for n, code in r["wrappers"]] or ["- none"]
    L += ["", "## Functions annotated KOKKOS_INLINE_FUNCTION", "- " + (", ".join(r["annotated"]) or "none"), ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("-r", "--report", default=None)
    args = ap.parse_args()

    p = Path(args.input)
    draft, report = kokkosify(p.read_text(), p.name)
    rep = format_report(report, p.name)

    out = args.out or str(p.with_suffix("")) + ".kokkosified.h"
    repout = args.report or str(p.with_suffix("")) + ".kokkosify-report.md"
    (sys.stdout.write(draft) if out == "-" else (Path(out).write_text(draft), print(f"draft:  {out}")))
    (sys.stdout.write(rep) if repout == "-" else (Path(repout).write_text(rep), print(f"report: {repout}")))


if __name__ == "__main__":
    main()
