"""Exact (git ground-truth) count of Fortran source files translated per run,
cross-checked against the self-reported `- [x]` checklist counts in
agent_log.md (parse_coverage.coverage_for_run), which can drift from what
actually landed in the submodule (see MISMATCHES below).

Each translated routine in software/mcfm follows one of two patterns relative
to the shared fork point (BASE_REF):
  - rename:  src/<mod>/X.f -> src/<mod>/deprecated/X.f   (git sees this as R100)
  - delete:  src/<mod>/X.f removed outright (no matching rename pair, but a
             new src/<mod>/X.cpp appears alongside it)
Both replace the original with new src/<mod>/{X.cpp, X_fi.F90, and often a
shared X.hpp or per-module .hpp}. We count ONE original file's removal as ONE
translated file — the new .cpp/.hpp/_fi.F90 outputs of that same translation
are not counted again, and shared-infrastructure edits (CMakeLists.txt,
Modules_Interface.f90 etc., which never remove an original source file) count
as zero.

Do not trust archive_summary.json's "archive_branch" field as the branch
name — for at least one run (08-11-2026/csloop-opus-5) it names a branch that
doesn't exist ("codescribe-opus-5"); the branch that actually exists is named
after the run directory itself ("csloop-opus-5"). Branch names are resolved
here from the run directory name, with an explicit existence check.
"""

import subprocess
from pathlib import Path

MCFM_DIR = Path(__file__).parent.parent.parent / "software" / "mcfm"
BASE_REF = "1abdcddaad89582552edc41de68e4a6e1ac75f1d"  # shared fork point for every evals/* branch seen so far


def _git(*args):
    result = subprocess.run(
        ["git", "-C", str(MCFM_DIR), *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def _resolve_branch_ref(day, run_name):
    """Prefer the remote ref (always present); fall back to a local branch of
    the same name if origin/... doesn't resolve."""
    for candidate in (f"origin/evals/{day}/{run_name}", f"evals/{day}/{run_name}"):
        try:
            _git("rev-parse", "--verify", candidate)
            return candidate
        except subprocess.CalledProcessError:
            continue
    return None


def translated_file_count(day, run_name):
    """Exact count of original Fortran files retired (renamed to deprecated/
    or deleted outright) under src/, relative to BASE_REF. Returns None if the
    branch can't be found."""
    ref = _resolve_branch_ref(day, run_name)
    if ref is None:
        return None
    diff = _git("diff", "--name-status", BASE_REF, ref, "--", "src/")
    renamed = 0
    deleted = 0
    for line in diff.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and status != "R100":
            continue  # partial-similarity renames aren't seen in practice; be conservative
        if status == "R100":
            renamed += 1
        elif status == "D" and parts[1].rstrip().lower().endswith((".f", ".f90")):
            deleted += 1
    return renamed + deleted


if __name__ == "__main__":
    for day, run_name in [
        ("08-11-2026", "csloop-opus-5"),
        ("08-11-2026", "csloop-opus-5-with-reasoning"),
        ("08-12-2026", "ccworkflow-sonnet-5-opus-5-integrate"),
        ("08-12-2026", "codescribe-opus-5-run2"),
        ("08-12-2026", "codescribe-opus-5-with-reasoning"),
        ("08-12-2026", "codescribe-kimi-k3-5"),
    ]:
        print(day, run_name, translated_file_count(day, run_name))
