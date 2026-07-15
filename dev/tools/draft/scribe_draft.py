#!/usr/bin/env python3
"""scribe_draft.py — the DRAFT phase of the staged translation workflow.

Replicates CodeScribe's `draft` step (annotate_fortran_file + isolate_scalar_functions
+ filter_file_indexes, codescribe/lib/_filetools.py) as a self-contained tool. Given
one Fortran source file and the Doxygen-derived symbol index (built by the INDEX
phase, dev/tools/index/build_roadmap.py -> dev/tools/assets/symbol_index.json), it emits a machine-
generated `<base>.scribe` draft: a set of `scribe-prompt:` hints followed by a
mechanically converted body (use->using namespace, real->double, complex(dp)->
complex<double>, dimension->FArray, x**n->pow, comment stripping, line continuations).

The draft is NOT a finished translation — it is scaffolding the translator (the
Author phase / translate skill) reads alongside the Spec's worked examples
(seed_examples.toml) and refines into the real <base>.cpp/.hpp/_fi.F90. Its value is
the hint block: it flags which called constructs are external functions defined in
other files (so the translator does not fabricate them, desired_spec.md §2 rule 9a)
and which are array/statement functions.

Usage:
  python3 dev/tools/draft/scribe_draft.py <fortran_file> [--index PATH] [-o OUT] [--force] [--stdout]
    --index  symbol index (default dev/tools/assets/symbol_index.json)
    -o       output path (default <base>.scribe next to the source)
    --stdout print to stdout instead of writing a file
"""
import argparse
import json
import os
import re
import sys

RE_FUNC_DECL = re.compile(r"^\s*function\s+(\w+)", re.IGNORECASE)
RE_VAR_DECL = re.compile(
    r"^\s*(integer|real|double|complex\(dp\)|bool|character)\s*::\s*([^;]*)", re.IGNORECASE)
RE_CALLS = re.compile(r"\b(\w+)\s*\(")
RE_USE = re.compile(r"^\s*use\s+(\w+)", re.IGNORECASE)
RE_CALL = re.compile(r"^\s*call\s+(\w+)", re.IGNORECASE)


def isolate_scalar_functions(path):
    """(scalars used as functions, all function-call names) — CodeScribe-faithful."""
    scalar_vars, calls, defined = set(), set(), set()
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            m = RE_FUNC_DECL.match(line)
            if m:
                defined.add(m.group(1))
            v = RE_VAR_DECL.match(line)
            if v:
                for var in v.group(2).split(","):
                    scalar_vars.add(var.strip().split("(")[0])
            for name in RE_CALLS.findall(line):
                calls.add(name)
    return (scalar_vars & calls) - defined, calls


def filter_symbols(path, symbols, function_calls):
    """Subset of the symbol index used by this file (via use/call/function calls)."""
    used_modules, used_subs = set(), set()
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            m = RE_USE.match(line)
            if m:
                used_modules.add(m.group(1).lower())
            c = RE_CALL.match(line)
            if c:
                used_subs.add(c.group(1).lower())
    calls_lower = {f.lower() for f in function_calls}
    self_rel = os.path.basename(path)
    return {
        name: rel for name, rel in symbols.items()
        if (name in used_modules or name in used_subs or name in calls_lower)
        and os.path.basename(rel) != self_rel
    }


def annotate(path, symbols):
    scalar_functions, function_calls = isolate_scalar_functions(path)
    filtered = filter_symbols(path, symbols, function_calls) if symbols else {}

    header_includes = {"#include <cmath>", "#include <complex>"}
    prompt_lines = [
        'scribe-prompt: Write corresponding extern "C" with _wrapper added to the name. '
        "Refer to the seed examples for treating FArray and scalars.",
        "scribe-prompt: When variables are used as functions they should be treated as "
        "external or statement functions. External functions are available in header files.",
        "scribe-prompt: Statement functions should be converted to equivalent lambda "
        "functions in C++. Include [&] in the capture clause to use variables by reference.",
    ]
    for c in sorted(function_calls):
        if c.lower() in filtered:
            prompt_lines.append(f"scribe-prompt: {c} is an external function (defined in {filtered[c.lower()]})")
    for c in sorted(scalar_functions):
        prompt_lines.append(f"scribe-prompt: {c} is an array or statement function")

    content = []
    with open(path, errors="replace") as fh:
        for raw in fh:
            s = raw.strip()
            low = s.lower()
            if low.startswith(("c", "!!", "!")) and not low.startswith(("complex", "call")):
                continue
            u = RE_USE.match(s)
            if u:
                header_includes.add(f"#include <{u.group(1)}.hpp>")
                content.append(f"using namespace {u.group(1)};\n")
                continue
            line = re.sub(r"implicit none", "", raw)
            line = re.sub(r"\binteger\b\s*", "int ", line, flags=re.IGNORECASE)
            line = re.sub(r"\breal\s*(\(\s*kind\s*=\s*\w+\s*\)|\(\s*\w+\s*\)|)?\s*", "double ", line, flags=re.IGNORECASE)
            line = re.sub(r"\bcomplex\s*\(\s*dp\s*\)\s*", "complex<double> ", line, flags=re.IGNORECASE)
            line = re.sub(r"(?<!std::)\s*::", "", line)
            line = re.sub(r"\bcomplex<([^>]+)>\s*(\w+)\s*\((.*?)\)\s*", r"FArray<std::complex<\1>> \2(\3)", line)
            line = re.sub(r"\b(real|double|int|bool|complex<[^>]+>)\s*,?\s*dimension\s*\((.*?)\)\s*(\w+)\s*;",
                          r"FArray<\1> \3(\2)", line, flags=re.IGNORECASE)
            line = re.sub(r"^\s*&", r"\\", line)
            line = re.sub(r"\s*&\s*$", r" \\", line)
            line = re.sub(r"(\w+)\s*\*\*\s*(\d+)", r"pow(\1,\2)", line)
            content.append(line.strip() + "\n")

    out = ["\n".join(prompt_lines), "\n\n", "\n".join(sorted(header_includes)) + "\n\n"]
    out.extend(content)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fortran_file")
    ap.add_argument("--index", default=None)
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    src = os.path.abspath(args.fortran_file)
    if not os.path.isfile(src):
        sys.exit(f"error: file not found: {src}")

    project = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    index_path = args.index or os.path.join(project, "dev", "tools", "assets", "symbol_index.json")
    symbols = {}
    if os.path.isfile(index_path):
        with open(index_path) as fh:
            symbols = (json.load(fh) or {}).get("symbols", {})
    else:
        print(f"warning: no symbol index at {index_path} — run the INDEX phase first "
              f"(python3 dev/tools/index/build_roadmap.py); external-function hints will be omitted",
              file=sys.stderr)

    draft = annotate(src, symbols)

    if args.stdout:
        sys.stdout.write(draft)
        return
    out = args.output or (os.path.splitext(src)[0] + ".scribe")
    if os.path.exists(out) and not args.force:
        print(f"skipping (exists): {out}  (use --force to overwrite)")
        return
    with open(out, "w") as fh:
        fh.write(draft)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
