#!/usr/bin/env python3
"""Draft tool — a mechanical first cut of one Fortran file, with hints.

The second step of stage-1 authoring. Given a Fortran source and the symbol index
(from the Index tool), it writes a `<base>.scribe` draft: a block of `scribe-prompt:`
hints followed by a rough, mechanically converted body (use → using namespace,
real → double, dimension → FArray, x**n → pow, comments stripped).

The draft is scaffolding, not an answer — the Author subagent reads it alongside the
worked examples in seed_examples.toml and the Spec, then writes the real translation.
Its value is the hint block: it flags which called names are external functions
defined elsewhere (so the model does not fabricate them; the Spec's rewrite rules — don't invent a called name).

By default the draft is written under dev/tmp/drafts/ (the scratch root, git-ignored),
mirroring the file's path below src/; pass -o to override.

Usage: scribe_draft.py <file.f> [--index PATH] [-o OUT] [--force] [--stdout]
"""
import argparse, json, os, re, sys

RE_USE  = re.compile(r"^\s*use\s+(\w+)", re.I)
RE_CALL = re.compile(r"^\s*call\s+(\w+)", re.I)
RE_NAME = re.compile(r"\b(\w+)\s*\(")


def external_hints(path, symbols):
    """Names this file calls that are defined in *other* files (rule 9a)."""
    used, self_base = set(), os.path.basename(path)
    with open(path, errors="replace") as fh:
        for line in fh:
            for m in (RE_USE.match(line), RE_CALL.match(line)):
                if m: used.add(m.group(1).lower())
            for name in RE_NAME.findall(line):
                used.add(name.lower())
    return {n: rel for n, rel in symbols.items()
            if n in used and os.path.basename(rel) != self_base}


def annotate(path, symbols):
    hints = [
        'scribe-prompt: Add an extern "C" <name>_wrapper; see the seed examples for FArray/scalar handling.',
        "scribe-prompt: A variable used as a function is an external or statement function.",
    ]
    for name, rel in sorted(external_hints(path, symbols).items()):
        hints.append(f"scribe-prompt: {name} is an external function (defined in {rel})")

    includes, body = {"#include <cmath>", "#include <complex>"}, []
    with open(path, errors="replace") as fh:
        for raw in fh:
            s = raw.strip(); low = s.lower()
            if low.startswith(("c ", "!")) and not low.startswith(("complex", "call")):
                continue
            u = RE_USE.match(s)
            if u:
                includes.add(f"#include <{u.group(1)}.hpp>")
                body.append(f"using namespace {u.group(1)};")
                continue
            line = re.sub(r"implicit none", "", raw)
            line = re.sub(r"\binteger\b", "int", line, flags=re.I)
            line = re.sub(r"\breal\s*(\([^)]*\))?", "double", line, flags=re.I)
            line = re.sub(r"\bcomplex\s*\(\s*dp\s*\)", "complex<double>", line, flags=re.I)
            line = re.sub(r"(?<!std)::", "", line)
            line = re.sub(r"\b(double|int|complex<[^>]+>)\s*,?\s*dimension\s*\((.*?)\)\s*(\w+)",
                          r"FArray<\1> \3(\2)", line, flags=re.I)
            line = re.sub(r"(\w+)\s*\*\*\s*(\d+)", r"pow(\1,\2)", line)
            body.append(line.rstrip())
    return "\n".join(hints) + "\n\n" + "\n".join(sorted(includes)) + "\n\n" + "\n".join(body) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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
    index = args.index or os.path.join(project, "dev/tmp/assets/symbol_index.json")
    symbols = {}
    if os.path.isfile(index):
        with open(index) as fh:
            symbols = (json.load(fh) or {}).get("symbols", {})
    else:
        print(f"warning: no symbol index at {index} — run the Index tool first; hints omitted", file=sys.stderr)

    draft = annotate(src, symbols)
    if args.stdout:
        sys.stdout.write(draft); return
    # Default output: dev/tmp/drafts/<path-below-src>.scribe (scratch, git-ignored),
    # keeping the MCFM clone clean. Mirror the sub-path under src/ to avoid collisions.
    rel = src.split("/src/", 1)[1] if "/src/" in src else os.path.basename(src)
    out = args.output or os.path.join(project, "dev/tmp/drafts", os.path.splitext(rel)[0] + ".scribe")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not args.force:
        print(f"skipping (exists): {out}  (use --force)"); return
    with open(out, "w") as fh:
        fh.write(draft)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
