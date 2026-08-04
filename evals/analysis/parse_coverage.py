"""Coverage / correctness facts per run: files settled, self-reported test
status, human-verified test status, and run status.

Everything here is derived from the actual log text, not hardcoded:
  - "files settled" = count of `- [x]` checklist items in the most-progressed
    agent_log.md for the run (for multi-attempt runs, agent_log.md accumulates
    across attempts, so we read the LAST attempt that has one).
  - "self-reported pass fraction" = the last `N/M ... PASS(ED)` match anywhere
    in that agent_log.md (the agent's own in-loop correctness claim).
  - "human-verified pass fraction" = the `SUMMARY: pass rate N/M` line a human
    appended after manually running the real MCFM regression suite, wherever a
    human_review file contains one.
  - "status" for multi-attempt csloop runs comes directly from the attempt
    directory's own name suffix (crashed / resume-crashed / resume-completed),
    which is the ground-truth label the experimenter gave each attempt.
"""

import re
from pathlib import Path

SELF_REPORT_RE = re.compile(r"(\d+)\s*/\s*(\d+)\D{0,20}PASS(?:ED)?", re.I)
VERIFIED_RE = re.compile(r"SUMMARY:\s*pass rate\s*(\d+)\s*/\s*(\d+)", re.I)
CHECKED_RE = re.compile(r"^\s*-\s*\[x\]", re.I | re.M)
UNCHECKED_RE = re.compile(r"^\s*-\s*\[ \]", re.M)


def _read(path):
    try:
        return Path(path).read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _find_agent_logs(run_dir):
    """All agent_log.md paths under this run, in attempt order (flat run -> single path)."""
    run_dir = Path(run_dir)
    direct = run_dir / "transformation" / "mcfm-translate" / "agent_log.md"
    if direct.exists():
        return [(None, direct)]

    found = []
    for attempt_dir in sorted(run_dir.glob("attempt*")):
        for candidate in ("transformations", "transformation"):
            path = attempt_dir / candidate / "mcfm-translate" / "agent_log.md"
            if path.exists():
                found.append((attempt_dir.name, path))
                break
    return found


def _find_human_reviews(run_dir):
    run_dir = Path(run_dir)
    reviews = []
    top = run_dir / "human_review"
    if top.exists():
        reviews.append((None, top))
    for attempt_dir in sorted(run_dir.glob("attempt*")):
        path = attempt_dir / "human_review"
        if path.exists():
            reviews.append((attempt_dir.name, path))
    return reviews


def _attempt_status(attempt_name):
    if attempt_name is None:
        return None
    suffix = attempt_name.split("-", 1)[1] if "-" in attempt_name else attempt_name
    return suffix  # e.g. "crashed", "resume-crashed", "resume-completed"


def coverage_for_run(run_dir):
    run_dir = Path(run_dir)
    agent_logs = _find_agent_logs(run_dir)

    settled = 0
    open_items = 0
    self_reported = None
    last_attempt_name = None
    if agent_logs:
        last_attempt_name, last_log_path = agent_logs[-1]
        text = _read(last_log_path)
        settled = len(CHECKED_RE.findall(text))
        open_items = len(UNCHECKED_RE.findall(text))
        matches = SELF_REPORT_RE.findall(text)
        if matches:
            n, m = matches[-1]
            self_reported = (int(n), int(m))

    human_verified = None
    for _, review_path in _find_human_reviews(run_dir):
        text = _read(review_path)
        m = VERIFIED_RE.search(text)
        if m:
            human_verified = (int(m.group(1)), int(m.group(2)))

    status = _attempt_status(last_attempt_name)
    if not agent_logs:
        # No agent_log.md anywhere under this run dir at all -> the run never executed
        # (e.g. csloop-gpt-5-4-effort-high, csloop-sonnet-4-6-with-reasoning-retries).
        status = "not-executed"
    elif status is None:
        # Flat (single-attempt) run: no attempt-name status label available.
        review_texts = " ".join(_read(p) for _, p in _find_human_reviews(run_dir))
        if "manually terminated" in review_texts.lower():
            status = "manually-terminated"
        elif review_texts.strip():
            status = "stopped (see human_review)"
        else:
            status = "stopped-at-gate"  # e.g. csloop-*-with-reasoning (07-24): 3/3 groups, no crash, no review needed

    return {
        "run_dir": str(run_dir),
        "files_settled": settled,
        "files_open": open_items,
        "self_reported_pass": self_reported,
        "human_verified_pass": human_verified,
        "final_status": status,
        "last_attempt": last_attempt_name or "single",
    }


if __name__ == "__main__":
    import sys
    from pprint import pprint

    pprint(coverage_for_run(sys.argv[1]))
