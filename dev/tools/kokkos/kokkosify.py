#!/usr/bin/env python3
"""kokkosify.py -- deterministic pre-pass for MCFM C++ -> Pepper Kokkos kernel drafts.

Applies the mechanical subset of dev/transformations/cpp-to-kokkos/desired_spec.md §3 to a stage-1
translated MCFM C++ file and emits:
  1. a DRAFT kernel body (NOT compilable as-is; the authoring agent finishes it), and
  2. a blocker/dependency report (the lint half of guide Step 1).

Zero tokens at run time; anything it cannot decide deterministically it flags instead
of guessing. The validation ladder (guide Step 4) is the safety net for the index
rewrites, exactly as it is for hand-written code.

Usage:
  kokkosify.py input.cpp [-o draft.h] [-r report.md]
With no -o/-r, draft goes to <input>.kokkosified.h and report to <input>.kokkosify-report.md
next to the input file. Pass '-' to print to stdout instead.

Transformations (safe, per guide section 3):
  - std::complex<double>            -> C
  - std:: math calls                -> Kokkos:: (fixed rename table)
  - KOKKOS_INLINE_FUNCTION          inserted before file-scope function definitions
  - FArrayND<T> name(a,b)           indexing name(i,j) -> name[(i)-1][(j)-1]
                                    (integer literals folded: p(1,4) -> p[0][3])
  - #include lines                  stripped and recorded; draft includes ../math.h

Flagged, never rewritten (report only):
  - QCDLoop calls (loopI1..4, qli*), STL containers/IO, throw/new/delete
  - module-global reads (*_mod)     -> candidate *_Params fields
  - FArray declarations             -> need fixed-size local arrays (agent decides sizes)
  - *_wrapper functions             -> dropped from kernels (C-ABI is stage-1 only)
  - cross-file calls (spinoru, dot, sub-amplitudes) -> inline or reuse decision
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# rename tables (guide section 3)
# ---------------------------------------------------------------------------

# std:: math -> Kokkos:: ; order matters only for report readability.
# std::abs covers both real and complex in Kokkos (Kokkos::abs(complex) exists);
# the |z|^2 -> re*re+im*im rewrite is left to the agent (semantic, needs context).
MATH_RENAMES = [
    "sqrt", "cbrt", "exp", "log", "log10", "pow",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "fabs", "abs", "conj", "hypot", "fmax", "fmin",
]

COMPLEX_T = re.compile(r"std::complex\s*<\s*double\s*>")

# things that cannot exist in device code -- report as blockers with line numbers
BLOCKER_PATTERNS = [
    (re.compile(r"\bloopI[1-4]\b"), "QCDLoop scalar integral -> analytic closed form (guide section 5)"),
    (re.compile(r"\bqli\w*\b"), "QCDLoop internal call -> analytic closed form (guide section 5)"),
    (re.compile(r"\bstd::vector\b"), "STL container -> fixed-size local array"),
    (re.compile(r"\bstd::map\b"), "STL container -> fixed-size local array / switch"),
    (re.compile(r"\bstd::string\b"), "std::string -> not allowed in device code"),
    (re.compile(r"\bstd::c(out|err)\b"), "host I/O -> remove (device code)"),
    (re.compile(r"\bprintf\s*\("), "printf -> remove or guard host-only"),
    (re.compile(r"\bthrow\b"), "exception -> Kokkos::abort() or restructure"),
    (re.compile(r"\bnew\b|\bdelete\b"), "heap allocation -> fixed-size local array"),
]

# cross-file calls worth listing for the inline-or-reuse decision (guide Step 1.4)
KNOWN_HELPERS = re.compile(r"\b(spinoru|spinorz|dot|lnrat|ddilog|L[01]|Lsm1)\s*\(")


# ---------------------------------------------------------------------------
# small scanner helpers
# ---------------------------------------------------------------------------

def find_matching_paren(text: str, open_idx: int) -> int:
    """Index of the ')' matching text[open_idx] == '(', or -1."""
    depth = 0
    for k in range(open_idx, len(text)):
        c = text[k]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return k
    return -1


def split_top_level_commas(s: str):
    """Split argument list on commas not nested in (), [], <> or {}."""
    parts, depth, start = [], 0, 0
    for k, c in enumerate(s):
        if c in "([<{":
            depth += 1
        elif c in ")]>}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(s[start:k])
            start = k + 1
    parts.append(s[start:])
    return parts


def shift_index(expr: str) -> str:
    """Turn a 1-based Fortran-style index expression into 0-based C.

    Integer literals fold (4 -> 3); anything else gets a textual -1 with parens.
    """
    e = expr.strip()
    if re.fullmatch(r"[+-]?\d+", e):
        return str(int(e) - 1)
    # j+1 -> j, j-1 -> j-2 : fold trailing +/- integer if present
    m = re.fullmatch(r"(.+?)\s*([+-])\s*(\d+)", e)
    if m:
        base, sign, off = m.group(1).strip(), m.group(2), int(m.group(3))
        off = off - 1 if sign == "+" else -off - 1
        if off == 0:
            return base
        return f"{base}{'+' if off > 0 else ''}{off}"
    return f"({e})-1"


def rewrite_farray_indexing(text: str, names: dict) -> str:
    """Rewrite name(i[,j...]) -> name[i-1][j-1]... for known FArray names.

    Processes the whole text repeatedly until no change so nested references
    (za(jp(1), k) etc.) are handled from the inside out.
    """
    if not names:
        return text
    call_re = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\s*\(")
    changed = True
    while changed:
        changed = False
        out, pos = [], 0
        for m in call_re.finditer(text):
            open_idx = m.end() - 1
            close_idx = find_matching_paren(text, open_idx)
            if close_idx < 0:
                continue
            args = split_top_level_commas(text[open_idx + 1 : close_idx])
            rank = names[m.group(1)]
            if len(args) != rank:  # not an indexing expression (e.g. a decl) -> skip
                continue
            if any(call_re.search(a) for a in args):
                continue  # inner references first; next sweep catches this one
            repl = m.group(1) + "".join(f"[{shift_index(a)}]" for a in args)
            out.append(text[pos : m.start()])
            out.append(repl)
            pos = close_idx + 1
            changed = True
        out.append(text[pos:])
        text = "".join(out)
    return text


# ---------------------------------------------------------------------------
# main pass
# ---------------------------------------------------------------------------

def kokkosify(src: str, src_name: str):
    report = {
        "includes": [], "blockers": [], "globals": set(), "using_mods": set(),
        "farrays": [], "wrappers": [], "helpers": set(), "annotated": [],
    }
    lines = src.splitlines()

    # -- scan phase (line-numbered, on the original text) --------------------
    # type group handles one level of template nesting (std::complex<double>)
    farray_decl = re.compile(
        r"\bFArray([1-4])D\s*<\s*((?:[^<>]|<[^<>]*>)*?)\s*>\s*&?\s*(\w+)\s*(\(|[;,)])")
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#include"):
            report["includes"].append((n, stripped))
        for pat, why in BLOCKER_PATTERNS:
            if pat.search(line):
                report["blockers"].append((n, stripped[:90], why))
        for m in re.finditer(r"\busing\s+namespace\s+(\w+_mod)\s*;", line):
            report["using_mods"].add(m.group(1))
        for m in re.finditer(r"\b(\w+_mod)::(\w+)", line):
            report["globals"].add(f"{m.group(1)}::{m.group(2)}")
        for m in farray_decl.finditer(line):
            rank, ftype = int(m.group(1)), m.group(2).strip()
            # Walk the declarator list: `FArray2D<T> za(a,b), zb(a,b);` declares
            # both names. First declarator starts at m.group(3).
            pos = m.start(3)
            while True:
                dm = re.match(r"(\w+)\s*(\(|[;,)=])", line[pos:])
                if not dm:
                    break
                name, delim = dm.group(1), dm.group(2)
                # Lower bounds: ctors are (sizes...) or (ptr, sizes...) with start
                # offsets appended (default 1). Explicit starts != 1 make the -1
                # shift WRONG (e.g. msqv is -nf..nf) -> flag, don't rewrite.
                # MCFM convention: msq*-named flavor arrays are ALWAYS -nf..nf,
                # even when only visible as a reference param -> denylist.
                shiftable = not name.startswith("msq")
                end = pos + dm.end()
                if delim == "(" and shiftable:
                    open_idx = end - 1
                    close_idx = find_matching_paren(line, open_idx)
                    if close_idx > 0:
                        args = [a.strip() for a in
                                split_top_level_commas(line[open_idx + 1 : close_idx])]
                        if len(args) > rank + 1:  # explicit start offsets
                            shiftable = all(a == "1" for a in args[-rank:])
                        end = close_idx + 1
                    else:
                        shiftable = False  # decl spans lines; be conservative
                elif delim == "(":
                    close_idx = find_matching_paren(line, end - 1)
                    end = close_idx + 1 if close_idx > 0 else end
                report["farrays"].append((n, name, rank, ftype, shiftable))
                # continue only if another declarator follows on this line
                nxt = re.match(r"\s*,\s*", line[end:])
                if not nxt:
                    break
                pos = end + nxt.end()
        if re.search(r"\b\w+_wrapper\s*\(", line):
            report["wrappers"].append((n, stripped[:90]))
        for m in KNOWN_HELPERS.finditer(line):
            report["helpers"].add(m.group(1))
        # unqualified math calls: not renamed (could shadow a real function);
        # device-callability is not guaranteed for bare ::log etc. -> report
        for m in re.finditer(
                r"(?<![:\w.])(sqrt|log|exp|pow|atan2|atan|sin|cos|abs|conj)\s*\(", line):
            report.setdefault("bare_math", set()).add(m.group(1))

    # unqualified globals from `using namespace *_mod`: report the mods; the
    # agent resolves which symbols leak in (needs the mod headers -> not deterministic)

    # -- rewrite phase --------------------------------------------------------
    text = src

    # 1. FArray indexing -> 0-based [][]. Only names whose EVERY declaration is
    #    provably default-1-based are rewritten; negative-lower-bound arrays
    #    (msqv etc.) keep their () syntax and are flagged in the report.
    #    Declaration lines themselves are left untouched (they get commented in
    #    step 6 as fixed-size-array TODOs).
    names, banned = {}, set()
    for (_, name, rank, _, shiftable) in report["farrays"]:
        if shiftable:
            names.setdefault(name, rank)
        else:
            banned.add(name)
    for b in banned:
        names.pop(b, None)
    decl_line = re.compile(r"\bFArray[1-4]D\b")
    rewritten = [
        line if decl_line.search(line) else rewrite_farray_indexing(line, names)
        for line in text.splitlines()
    ]
    text = "\n".join(rewritten)

    # 2. complex type
    text = COMPLEX_T.sub("C", text)

    # 3. math namespace
    for fn in MATH_RENAMES:
        text = re.sub(rf"\bstd::{fn}\b", f"Kokkos::{fn}", text)

    # 4. strip includes (recorded above); strip using-namespace *_mod lines
    #    (globals become Params fields -- agent wires them)
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#include"):
            continue
        if re.match(r"using\s+namespace\s+\w+_mod\s*;", s):
            kept.append("// KOKKOSIFY-TODO(params): was `%s` -> move reads into *_Params" % s)
            continue
        kept.append(line)
    text = "\n".join(kept)

    # 5. annotate file-scope function definitions. Conservative: a line that
    #    starts (no indent) with a known return type and has '(' and no ';'.
    ret_types = r"(?:void|double|int|bool|C)"
    annotated = []
    out_lines = []
    for line in text.splitlines():
        m = re.match(rf"^({ret_types})\s+(\w+)\s*\(", line)
        if m and not line.rstrip().endswith(";"):
            fname = m.group(2)
            if fname.endswith("_wrapper") or fname == "main":
                out_lines.append("// KOKKOSIFY-TODO(drop): stage-1 C-ABI artifact, not device code:")
                out_lines.append("// " + line)
                continue
            out_lines.append("KOKKOS_INLINE_FUNCTION")
            annotated.append(fname)
        out_lines.append(line)
    text = "\n".join(out_lines)
    report["annotated"] = annotated

    # 6. FArray declaration lines: flag (sizes like mxpart are host constants;
    #    kernel wants tight fixed sizes -- an agent decision)
    flagged = []
    for line in text.splitlines():
        if re.search(r"\bFArray[1-4]D\b", line):
            flagged.append("// KOKKOSIFY-TODO(array): fixed-size local array instead of FArray:")
            flagged.append("// " + line.strip())
        else:
            flagged.append(line)
    text = "\n".join(flagged)

    banner = (
        "// MACHINE-GENERATED DRAFT (kokkosify.py) from %s -- NOT compilable as-is.\n"
        "// Mechanical renames + index shifts applied; every KOKKOSIFY-TODO needs a\n"
        "// decision. Follow dev/transformations/cpp-to-kokkos/desired_spec.md sections 2-4 to finish.\n"
        "#pragma once\n"
        '#include "../math.h"\n' % src_name
    )
    return banner + "\n" + text + "\n", report


def format_report(report, src_name: str) -> str:
    L = [f"# kokkosify report -- {src_name}", ""]
    L.append("## Blockers (must be resolved; guide section 3/5)")
    if report["blockers"]:
        L += [f"- L{n}: `{code}` -- {why}" for (n, code, why) in report["blockers"]]
    else:
        L.append("- none found")
    L.append("")
    L.append("## Candidate *_Params fields (module globals read)")
    L += [f"- `{g}`" for g in sorted(report["globals"])] or ["- none"]
    if report["using_mods"]:
        L.append("")
        L.append("Unqualified reads possible via `using namespace`: " +
                 ", ".join(sorted(report["using_mods"])) +
                 " -- check the mod headers for symbols used without a prefix.")
    L.append("")
    L.append("## FArray declarations -> fixed-size local arrays (agent sizes them)")
    L += [f"- L{n}: `{name}` rank {rank} of `{t}`"
          + ("" if shiftable else " -- NON-DEFAULT LOWER BOUNDS: () indexing kept, agent must remap (e.g. msqv is -nf..nf)")
          for (n, name, rank, t, shiftable) in report["farrays"]] or ["- none"]
    L.append("")
    if report.get("bare_math"):
        L.append("## Unqualified math calls (not renamed; verify device-callable or qualify Kokkos::)")
        L.append("- " + ", ".join(sorted(report["bare_math"])))
        L.append("")
    L.append("## Cross-file helper calls (inline or reuse an already-ported kernel helper)")
    L += [f"- `{h}`" for h in sorted(report["helpers"])] or ["- none"]
    L.append("")
    L.append("## Dropped / flagged")
    L += [f"- wrapper at L{n}: `{code}`" for (n, code) in report["wrappers"]] or ["- no wrappers"]
    L.append("")
    L.append("## Functions annotated KOKKOS_INLINE_FUNCTION")
    L.append("- " + (", ".join(report["annotated"]) or "none"))
    L.append("")
    L.append("## Original includes (draft replaces all with ../math.h)")
    L += [f"- L{n}: `{inc}`" for (n, inc) in report["includes"]] or ["- none"]
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="stage-1 MCFM C++ file")
    ap.add_argument("-o", "--out", default=None, help="draft output path ('-' = stdout)")
    ap.add_argument("-r", "--report", default=None, help="report output path ('-' = stdout)")
    args = ap.parse_args()

    p = Path(args.input)
    src = p.read_text()
    draft, report = kokkosify(src, p.name)
    rep = format_report(report, p.name)

    out = args.out or str(p.with_suffix("")) + ".kokkosified.h"
    repout = args.report or str(p.with_suffix("")) + ".kokkosify-report.md"
    if out == "-":
        sys.stdout.write(draft)
    else:
        Path(out).write_text(draft)
        print(f"draft:  {out}")
    if repout == "-":
        sys.stdout.write(rep)
    else:
        Path(repout).write_text(rep)
        print(f"report: {repout}")


if __name__ == "__main__":
    main()
