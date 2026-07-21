"""Cleanup analysis tool — inspect translated MCFM families for conservative cleanup actions.

  python3 dev/tools/cleanup/analyze_cleanup.py
  python3 dev/tools/cleanup/analyze_cleanup.py --json

Reads `dev/tmp/assets/cleanup_index.json` when available, otherwise performs the same repository
scan directly. Prints a human-readable report and can emit JSON to stdout.
"""
import os
import sys
import json
import re
import collections

ROOT = os.environ.get("PROJECT_HOME") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MCFM = os.environ.get("MCFM_HOME", ROOT + "/software/mcfm")
SRC = MCFM + "/src"
ASSETS = ROOT + "/dev/tmp/assets"
CLEANUP_JSON = ASSETS + "/cleanup_index.json"
HEADER_RE = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]')
TARGET_RE = re.compile(r'^\s*target_sources\s*\(')


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def collect_cmake_sources(root):
    cmake_sources = collections.defaultdict(set)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        if "CMakeLists.txt" not in files:
            continue
        text = read_text(os.path.join(dirpath, "CMakeLists.txt"))
        if not text or not TARGET_RE.search(text):
            continue
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("target_sources(") or line == ")":
                continue
            if any(line.endswith(ext) for ext in (".f", ".F", ".f90", ".F90", ".cpp", ".hpp", ".h")):
                cmake_sources[os.path.relpath(dirpath, root)].add(line)
    return cmake_sources


def collect_header_usage(root):
    usage = collections.Counter()
    users = collections.defaultdict(set)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        for fn in files:
            if not fn.endswith((".cpp", ".hpp", ".h", ".cc", ".cxx")):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            text = read_text(path)
            for line in text.splitlines():
                m = HEADER_RE.match(line)
                if not m:
                    continue
                inc = m.group(1).replace("\\", "/")
                usage[inc] += 1
                users[inc].add(rel)
                base = os.path.basename(inc)
                if base != inc:
                    usage[base] += 1
                    users[base].add(rel)
    return usage, users


def scan_cleanup(root):
    cmake_sources = collect_cmake_sources(root)
    header_usage, header_users = collect_header_usage(root)
    families = collections.defaultdict(dict)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ("deprecated", "Store", "working")]
        rel_dir = os.path.relpath(dirpath, root)
        for fn in files:
            full = os.path.join(dirpath, fn)
            base, ext = os.path.splitext(fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if base.endswith("_fi") and ext in (".f", ".F", ".f90", ".F90"):
                families[(rel_dir, base[:-3])]["fi"] = rel
                continue
            if ext in (".f", ".F", ".f90", ".F90"):
                families[(rel_dir, base)]["fortran"] = rel
            elif ext == ".cpp":
                families[(rel_dir, base)]["cpp"] = rel
            elif ext in (".hpp", ".h"):
                families[(rel_dir, base)]["header"] = rel

    out = []
    for (rel_dir, base), parts in sorted(families.items()):
        original = parts.get("fortran", "")
        cpp = parts.get("cpp", "")
        header = parts.get("header", "")
        fi = parts.get("fi", "")
        local_cmake_entries = cmake_sources.get(rel_dir, set())
        header_name = os.path.basename(header) if header else ""
        include_count = header_usage.get(header_name, 0) if header_name else 0
        out.append({
            "base": (("" if rel_dir == "." else rel_dir + "/") + base),
            "dir": rel_dir,
            "fortran": original,
            "cpp": cpp,
            "header": header,
            "fi": fi,
            "deprecated_original": int(bool(original and "/deprecated/" in original)),
            "cmake_original": int(bool(original and os.path.basename(original) in local_cmake_entries)),
            "cmake_cpp": int(bool(cpp and os.path.basename(cpp) in local_cmake_entries)),
            "cmake_header": int(bool(header and os.path.basename(header) in local_cmake_entries)),
            "cmake_fi": int(bool(fi and os.path.basename(fi) in local_cmake_entries)),
            "header_include_count": include_count,
            "header_users": sorted(header_users.get(header_name, set())),
            "move_candidate": int(bool(original and cpp and "/deprecated/" not in original)),
            "delete_shim_candidate": int(bool(fi and cpp and not (original and os.path.basename(original) in local_cmake_entries))),
            "merge_candidate": int(bool(cpp and header) and include_count <= 1),
        })
    return out


def load_candidates():
    if os.path.isfile(CLEANUP_JSON):
        try:
            with open(CLEANUP_JSON, encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("candidates", [])
        except (OSError, json.JSONDecodeError):
            pass
    return scan_cleanup(SRC)


def classify(row):
    actions = []
    reasons = []
    if row.get("move_candidate"):
        actions.append("MOVE_F")
    if row.get("delete_shim_candidate"):
        actions.append("DELETE_SHIM?")
    elif row.get("fi"):
        reasons.append("keep shim: original Fortran still appears in build or evidence is incomplete")
    if row.get("merge_candidate"):
        actions.append("MERGE_HPP_CPP?")
    elif row.get("header"):
        reasons.append(f"keep split: header include count {row.get('header_include_count', 0)}")
    if not actions:
        actions.append("NO_ACTION")
    return actions, reasons


def print_report(rows):
    print(f"# cleanup candidates under {SRC}")
    print("# base\tactions\tfortran\tcpp\tfi\theader\theader_uses")
    for row in rows:
        actions, _ = classify(row)
        print(
            f"{row.get('base','')}\t{','.join(actions)}\t{int(bool(row.get('fortran')))}\t"
            f"{int(bool(row.get('cpp')))}\t{int(bool(row.get('fi')))}\t{int(bool(row.get('header')))}\t"
            f"{row.get('header_include_count', 0)}"
        )
    print()
    for row in rows:
        actions, reasons = classify(row)
        if actions == ["NO_ACTION"] and not reasons:
            continue
        print(f"## {row.get('base','')}")
        print(f"- actions: {', '.join(actions)}")
        if row.get("header_users"):
            print(f"- header users: {', '.join(row['header_users'])}")
        for reason in reasons:
            print(f"- note: {reason}")


def main(argv):
    rows = load_candidates()
    if "--json" in argv:
        json.dump(rows, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    print_report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
