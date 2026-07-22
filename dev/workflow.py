#!/usr/bin/env python3
"""Unified workflow CLI for dev tooling.

Examples:
  python3 dev/workflow.py refresh
  python3 dev/workflow.py status
  python3 dev/workflow.py next mcfm-translate
  python3 dev/workflow.py gate mcfm-translate
  python3 dev/workflow.py approve mcfm-translate --latest-blocking
  python3 dev/workflow.py draft software/mcfm/src/.../file.f
  python3 dev/workflow.py verify software/mcfm/src/.../file.cpp -- u u~ e- e+
  python3 dev/workflow.py cleanup report
  python3 dev/workflow.py closure qqb_z
  python3 dev/workflow.py kokkos draft software/mcfm/src/.../file.cpp
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "dev" / "tools"
ASSETS = ROOT / "dev" / "tmp" / "assets"
TRANSFORMATIONS = {
    "mcfm-translate": ROOT / "dev" / "transformations" / "mcfm-translate",
    "mcfm-cleanup": ROOT / "dev" / "transformations" / "mcfm-cleanup",
    "pepper-kokkos-port": ROOT / "dev" / "transformations" / "pepper-kokkos-port",
}
COMMON = TOOLS / "common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
from approval_log import is_complete, is_open, load_approved_groups, parse_groups


def run(cmd: list[str]) -> int:
    return subprocess.run(cmd, cwd=ROOT).returncode


def transformation_dir(name: str) -> Path:
    try:
        return TRANSFORMATIONS[name]
    except KeyError:
        raise SystemExit(f"error: unknown transformation '{name}'")


def cmd_refresh(_: argparse.Namespace) -> int:
    rc = run([sys.executable, str(TOOLS / "index" / "build_roadmap.py"), "--doxygen"])
    if rc != 0:
        return rc
    return run([sys.executable, str(TOOLS / "index" / "build_roadmap.py")])


def summarize_groups(tdir: Path) -> str:
    log_path = tdir / "agent_log.md"
    approvals_path = tdir / "approvals.toml"
    if not log_path.exists():
        return "no agent_log.md yet"
    try:
        groups = parse_groups(log_path)
    except FileNotFoundError:
        return "no agent_log.md yet"
    approved = load_approved_groups(approvals_path)
    open_count = sum(1 for g in groups if is_open(g))
    complete_count = sum(1 for g in groups if is_complete(g))
    pending_count = sum(1 for g in groups if is_complete(g) and g["title"] not in approved)
    return f"groups: {len(groups)} total, {open_count} open, {complete_count} completed, {pending_count} pending approval"


def load_roadmap_rows() -> list[dict]:
    path = ASSETS / "roadmap_metrics.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def load_cleanup_rows() -> list[dict]:
    path = ASSETS / "cleanup_index.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return (json.load(fh) or {}).get("candidates", [])


def cmd_status(_: argparse.Namespace) -> int:
    print("# workflow status")
    print(f"assets: {(ASSETS if ASSETS.exists() else str(ASSETS) + ' (missing)')}")
    roadmap = load_roadmap_rows()
    cleanup = load_cleanup_rows()
    if roadmap:
        ready = [r for r in roadmap if r.get("deps") == "0" and r.get("blind") == "0"]
        print(f"roadmap metrics: {len(roadmap)} untranslated file rows, {len(ready)} ready leaves")
    else:
        print("roadmap metrics: missing (run `python3 dev/workflow.py refresh`)")
    if cleanup:
        moves = sum(int(r.get("move_candidate", 0)) for r in cleanup)
        shims = sum(int(r.get("delete_shim_candidate", 0)) for r in cleanup)
        merges = sum(int(r.get("merge_candidate", 0)) for r in cleanup)
        print(f"cleanup index: {len(cleanup)} families, move {moves}, shim-delete {shims}, merge {merges}")
    else:
        print("cleanup index: missing (run `python3 dev/workflow.py refresh`)")
    print()
    for name, tdir in TRANSFORMATIONS.items():
        print(f"- {name}: {summarize_groups(tdir)}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    if args.transformation == "mcfm-translate":
        rows = [r for r in load_roadmap_rows() if r.get("deps") == "0" and r.get("blind") == "0"]
        if not rows:
            print("no ready translation files found; run `python3 dev/workflow.py refresh`")
            return 0
        print("# next translation candidates")
        for row in rows[:10]:
            print(f"- {row['rel']}  (fanin={row['fanin']}, bench={row['bench']})")
        return 0

    if args.transformation == "mcfm-cleanup":
        rows = [
            r for r in load_cleanup_rows()
            if int(r.get("move_candidate", 0))
            or int(r.get("delete_shim_candidate", 0))
            or int(r.get("merge_candidate", 0))
        ]
        if not rows:
            print("no cleanup candidates found; run `python3 dev/workflow.py refresh`")
            return 0

        def score(row: dict) -> tuple[int, int, int]:
            return (
                int(row.get("delete_shim_candidate", 0)),
                int(row.get("move_candidate", 0)),
                int(row.get("merge_candidate", 0)),
            )

        rows.sort(key=score, reverse=True)
        print("# next cleanup candidates")
        for row in rows[:10]:
            actions = []
            if int(row.get("move_candidate", 0)):
                actions.append("MOVE_F")
            if int(row.get("delete_shim_candidate", 0)):
                actions.append("DELETE_SHIM?")
            if int(row.get("merge_candidate", 0)):
                actions.append("MERGE_HPP_CPP?")
            print(f"- {row['base']}  ({', '.join(actions)})")
        return 0

    print("# next Kokkos targets")
    print("Use `python3 dev/workflow.py closure <name>` on a candidate amplitude to check readiness.")
    print("Then choose bottom-up targets whose full closure is already in C++ and verified in step 1.")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    return run([
        sys.executable,
        str(TOOLS / "approve" / "check_gate.py"),
        str(transformation_dir(args.transformation)),
    ])


def cmd_approve(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(TOOLS / "approve" / "approve_group.py"),
        str(transformation_dir(args.transformation)),
        *args.args,
    ]
    return run(cmd)


def cmd_draft(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "draft" / "scribe_draft.py"), *args.args])


def cmd_verify(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "coverage" / "coverage_check.py"), *args.args])


def cmd_cleanup_report(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "cleanup" / "analyze_cleanup.py"), *args.args])


def cmd_closure(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "closure" / "calltree_closure.py"), args.name])


def cmd_kokkos_draft(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "kokkos" / "kokkosify.py"), *args.args])


def cmd_kokkos_validate(args: argparse.Namespace) -> int:
    return run([sys.executable, str(TOOLS / "kokkos" / "kokkosify.py"), "validate", *args.args])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified workflow CLI for the dev transformation pipeline.",
        epilog="Prefer this command over calling scripts in dev/tools/ directly.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("refresh", help="rebuild doxygen-derived roadmap assets")
    p.set_defaults(func=cmd_refresh)

    p = sub.add_parser("status", help="summarize workflow assets and transformation state")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("next", help="show the next likely targets for a transformation")
    p.add_argument("transformation", choices=sorted(TRANSFORMATIONS))
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("gate", help="check approval gate for a transformation")
    p.add_argument("transformation", choices=sorted(TRANSFORMATIONS))
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("approve", help="record/list approvals for a transformation")
    p.add_argument("transformation", choices=sorted(TRANSFORMATIONS))
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to approve_group.py")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("draft", help="create a stage-1 draft")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to scribe_draft.py")
    p.set_defaults(func=cmd_draft)

    p = sub.add_parser("verify", help="run stage-1 coverage verification")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to coverage_check.py")
    p.set_defaults(func=cmd_verify)

    cleanup = sub.add_parser("cleanup", help="cleanup workflow helpers")
    cleanup_sub = cleanup.add_subparsers(dest="cleanup_command", required=True)
    p = cleanup_sub.add_parser("report", help="report cleanup candidates")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to analyze_cleanup.py")
    p.set_defaults(func=cmd_cleanup_report)

    p = sub.add_parser("closure", help="show linked call-tree closure for one routine")
    p.add_argument("name")
    p.set_defaults(func=cmd_closure)

    kokkos = sub.add_parser("kokkos", help="stage-2 Kokkos helpers")
    kokkos_sub = kokkos.add_subparsers(dest="kokkos_command", required=True)
    p = kokkos_sub.add_parser("draft", help="run kokkosify draft pass")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to kokkosify.py")
    p.set_defaults(func=cmd_kokkos_draft)
    p = kokkos_sub.add_parser("validate", help="run Kokkos validator")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments forwarded to kokkosify.py validate")
    p.set_defaults(func=cmd_kokkos_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
