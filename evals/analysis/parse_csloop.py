"""Parse CodeScribe-loop ("csloop") run directories into flat rows.

Layout is inconsistent across runs — two shapes exist:
  - flat:   experiments/<day>/csloop-<variant>/metadata/{manifest.toml, loop_*.toml}
  - nested: experiments/<day>/csloop-<variant>/attemptNN-<status>/metadata/{...}

Each attempt directory is a fully independent run with its own run_id; manifest
`cumulative_*` fields do NOT carry over across attempts despite the "resume"
naming, so a harness-variant's true total is the sum across all its attempt
subdirectories. Some attempt dirs (e.g. attempt05-fix-failures, attempt03-resume
on 07-25) are entirely empty and must be skipped, as must fully-empty run dirs
like csloop-gpt-5-4-effort-high (no GPT-5.4 run was ever executed).

Per-loop token/tool-call data lives in loop_NNN_{author,review}.toml:
  [usage]       input, output, reasoning, cache_write, cache_read
  [tool_calls]  executed, ok, errors, rejected  (rejected = policy-blocked,
                                                  never executed; errors = executed
                                                  but ok=false in [[tools]])
"""

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from pathlib import Path


def _load_toml(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def find_attempt_dirs(run_dir):
    """Return every metadata/ dir under this run, whether flat or nested by attempt."""
    run_dir = Path(run_dir)
    metadata_dirs = []

    direct = run_dir / "metadata"
    if direct.is_dir():
        metadata_dirs.append((None, direct))

    for attempt_dir in sorted(run_dir.glob("attempt*")):
        meta = attempt_dir / "metadata"
        if meta.is_dir():
            metadata_dirs.append((attempt_dir.name, meta))

    return metadata_dirs


def parse_metadata_dir(metadata_dir):
    """Return one row per loop_*.toml file (per phase per loop) in this metadata dir."""
    manifest_path = metadata_dir / "manifest.toml"
    if not manifest_path.exists():
        return []

    manifest = _load_toml(manifest_path)
    run_info = manifest.get("run", {})
    model = run_info.get("model", "unknown")

    rows = []
    for loop_path in sorted(metadata_dir.glob("loop_*.toml")):
        try:
            loop_data = _load_toml(loop_path)
        except Exception as exc:
            print(f"  WARNING: failed to parse {loop_path}: {exc}")
            continue

        usage = loop_data.get("usage", {})
        tool_calls = loop_data.get("tool_calls", {})
        tools = loop_data.get("tools", [])
        rejected_calls = loop_data.get("rejected_calls", [])

        tool_ok = sum(1 for t in tools if t.get("ok"))
        tool_error = sum(1 for t in tools if not t.get("ok"))

        rows.append(
            {
                "loop_file": loop_path.name,
                "loop_index": loop_data.get("loop_index"),
                "phase": loop_data.get("phase", "unknown"),
                "model": loop_data.get("model", model),
                "stop_reason": loop_data.get("stop_reason"),
                "iterations": loop_data.get("iterations"),
                "duration_s": loop_data.get("duration_s", 0.0),
                "input_tokens": usage.get("input", 0),
                "output_tokens": usage.get("output", 0),
                "reasoning_tokens": usage.get("reasoning", 0),
                "cache_write_tokens": usage.get("cache_write", 0),
                "cache_read_tokens": usage.get("cache_read", 0),
                "tool_executed": tool_calls.get("executed", len(tools)),
                "tool_ok": tool_calls.get("ok", tool_ok),
                "tool_errors": tool_calls.get("errors", tool_error),
                "tool_rejected": tool_calls.get("rejected", len(rejected_calls)),
            }
        )
    return rows


def parse_csloop_run(run_dir):
    run_dir = Path(run_dir)
    rows = []
    for attempt_name, metadata_dir in find_attempt_dirs(run_dir):
        for row in parse_metadata_dir(metadata_dir):
            row["run_dir"] = str(run_dir)
            row["attempt"] = attempt_name or "single"
            rows.append(row)
    return rows


def parse_all_csloop(experiments_root):
    experiments_root = Path(experiments_root)
    all_rows = []
    for day_dir in sorted(experiments_root.iterdir()):
        if not day_dir.is_dir():
            continue
        for run_dir in sorted(day_dir.glob("csloop-*")):
            rows = parse_csloop_run(run_dir)
            if not rows:
                print(f"  (skipping {run_dir} — no usable metadata found)")
                continue
            for row in rows:
                row["day"] = day_dir.name
                row["run_name"] = run_dir.name
                all_rows.append(row)
    return all_rows


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "experiments"
    rows = parse_all_csloop(root)
    print(f"Parsed {len(rows)} csloop loop rows")
    for row in rows[:5]:
        print(row)
