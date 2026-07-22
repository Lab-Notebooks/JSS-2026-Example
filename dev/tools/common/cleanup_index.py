"""Shared cleanup index helpers for dev tooling."""
from __future__ import annotations

import collections
import os
import re
from pathlib import Path

HEADER_RE = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]')
TARGET_RE = re.compile(r'^\s*target_sources\s*\(')
SKIP_DIRS = {"deprecated", "Store", "working"}
SOURCE_EXTS = (".f", ".F", ".f90", ".F90")
CMAKE_EXTS = SOURCE_EXTS + (".cpp", ".hpp", ".h")
HEADER_EXTS = (".cpp", ".hpp", ".h", ".cc", ".cxx")


def read_text(path: str | Path) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def iter_source_tree(root: str | Path):
    root = os.fspath(root)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield dirpath, dirs, files


def collect_cmake_sources(root: str | Path):
    cmake_sources = collections.defaultdict(set)
    for dirpath, _, files in iter_source_tree(root):
        if "CMakeLists.txt" not in files:
            continue
        text = read_text(os.path.join(dirpath, "CMakeLists.txt"))
        if not text or not TARGET_RE.search(text):
            continue
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("target_sources(") or line == ")":
                continue
            if any(line.endswith(ext) for ext in CMAKE_EXTS):
                cmake_sources[os.path.relpath(dirpath, root)].add(line)
    return cmake_sources


def collect_header_usage(root: str | Path):
    usage = collections.Counter()
    users = collections.defaultdict(set)
    for dirpath, _, files in iter_source_tree(root):
        for fn in files:
            if not fn.endswith(HEADER_EXTS):
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


def build_cleanup_index(root: str | Path, cmake_sources=None, header_usage=None, header_users=None):
    root = os.fspath(root)
    cmake_sources = cmake_sources if cmake_sources is not None else collect_cmake_sources(root)
    if header_usage is None or header_users is None:
        header_usage, header_users = collect_header_usage(root)

    cleanup = []
    families = collections.defaultdict(dict)
    for dirpath, _, files in iter_source_tree(root):
        rel_dir = os.path.relpath(dirpath, root)
        for fn in files:
            full = os.path.join(dirpath, fn)
            base, ext = os.path.splitext(fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if base.endswith("_fi") and ext in SOURCE_EXTS:
                families[(rel_dir, base[:-3])]["fi"] = rel
                continue
            if ext in SOURCE_EXTS:
                families[(rel_dir, base)]["fortran"] = rel
            elif ext == ".cpp":
                families[(rel_dir, base)]["cpp"] = rel
            elif ext in (".hpp", ".h"):
                families[(rel_dir, base)]["header"] = rel

    for (rel_dir, base), parts in sorted(families.items()):
        rel_prefix = "" if rel_dir == "." else rel_dir + "/"
        original = parts.get("fortran", "")
        cpp = parts.get("cpp", "")
        header = parts.get("header", "")
        fi = parts.get("fi", "")
        original_name = os.path.basename(original) if original else ""
        deprecated_original = bool(original and "/deprecated/" in original)
        local_cmake_entries = cmake_sources.get(rel_dir, set())
        cmake_original = int(original_name in local_cmake_entries) if original_name else 0
        cmake_cpp = int(os.path.basename(cpp) in local_cmake_entries) if cpp else 0
        cmake_header = int(os.path.basename(header) in local_cmake_entries) if header else 0
        cmake_fi = int(os.path.basename(fi) in local_cmake_entries) if fi else 0
        header_key = os.path.basename(header) if header else ""
        include_count = header_usage.get(header_key, 0) if header_key else 0
        users = sorted(header_users.get(header_key, set())) if header_key else []
        cleanup.append({
            "base": rel_prefix + base,
            "dir": "." if rel_dir == "." else rel_dir,
            "fortran": original,
            "cpp": cpp,
            "header": header,
            "fi": fi,
            "deprecated_original": int(deprecated_original),
            "cmake_original": cmake_original,
            "cmake_cpp": cmake_cpp,
            "cmake_header": cmake_header,
            "cmake_fi": cmake_fi,
            "header_include_count": include_count,
            "header_users": users,
            "move_candidate": int(bool(original and cpp and not deprecated_original)),
            "delete_shim_candidate": int(bool(fi and cpp and not cmake_original)),
            "merge_candidate": int(bool(cpp and header) and include_count <= 1),
        })
    return cleanup
