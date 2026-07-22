#!/usr/bin/env python3
"""Record a human approval for a completed review group.

Usage:
  python3 dev/tools/approve/approve_group.py <transformation-dir> [<group-title>] [--by <name>] [--review-note <text>] [--force]
  python3 dev/tools/approve/approve_group.py <transformation-dir> --latest [--by <name>] [--review-note <text>] [--force]
  python3 dev/tools/approve/approve_group.py <transformation-dir> --list-pending
  python3 dev/tools/approve/approve_group.py <transformation-dir> --latest-blocking [--by <name>] [--review-note <text>] [--force]

Examples:
  python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --list-pending
  python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest
  python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup --latest-blocking
  python3 dev/tools/approve/approve_group.py dev/transformations/mcfm-cleanup "Group 1 — Mods/ Fortran bridge modules" --by Akash --review-note "revise kept header"
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from datetime import date
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "common"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))
from approval_log import load_approved_groups, load_toml, parse_groups, pending_groups, is_complete


def load_evaluate_gate():
    check_gate_path = Path(__file__).with_name("check_gate.py")
    spec = importlib.util.spec_from_file_location("check_gate_local", check_gate_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {check_gate_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_gate


evaluate_gate = load_evaluate_gate()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("transformation_dir")
    p.add_argument("group_title", nargs="?")
    p.add_argument("--by", default=os.environ.get("USER", ""))
    p.add_argument("--review-note", default="")
    p.add_argument("--force", action="store_true")
    p.add_argument("--latest", action="store_true", help="approve the oldest pending completed group")
    p.add_argument("--latest-blocking", action="store_true", help="approve the exact group currently blocking the gate")
    p.add_argument("--list-pending", action="store_true", help="list completed groups that are not yet approved")
    args = p.parse_args()
    if args.list_pending:
        return args
    modes = int(bool(args.latest)) + int(bool(args.latest_blocking)) + int(bool(args.group_title))
    if modes > 1:
        p.error("use exactly one of: explicit group title, --latest, or --latest-blocking")
    if modes == 0:
        p.error("provide a group title or use --latest or --latest-blocking or --list-pending")
    if not args.by:
        p.error("--by is required unless $USER is set")
    return args


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_toml(data: dict) -> str:
    out = ["version = 1", ""]
    for item in data.get("approval", []):
        out.append("[[approval]]")
        out.append(f'group = {toml_string(item["group"])}')
        out.append(f'date = {toml_string(item["date"])}')
        out.append(f'by = {toml_string(item["by"])}')
        out.append(f'decision = {toml_string(item.get("decision", "approved"))}')
        review_note = item.get("review_note", "")
        if review_note:
            out.append(f'review_note = {toml_string(review_note)}')
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    tdir = Path(args.transformation_dir)
    log_path = tdir / "agent_log.md"
    approvals_path = tdir / "approvals.toml"

    try:
        pending = pending_groups(log_path, approvals_path)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.list_pending:
        if not pending:
            print(f"no pending completed groups in {tdir}")
            return 0
        print(f"pending approvals in {tdir}:")
        for title in pending:
            print(f"  - {title}")
        return 0

    if args.latest_blocking:
        gate = evaluate_gate(tdir)
        if gate["state"] == "error":
            print(gate["message"], file=sys.stderr)
            return 2
        if gate["state"] != "blocked":
            print(f"no blocking group in {tdir}")
            return 0
        group_title = gate["group"]
    else:
        group_title = pending[0] if args.latest else args.group_title
    if args.latest and not pending:
        print(f"no pending completed groups in {tdir}")
        return 0
    if group_title is None:
        print("error: no group selected", file=sys.stderr)
        return 2

    groups = [g["title"] for g in parse_groups(log_path)]
    if group_title not in groups:
        print(f"error: group not found in {log_path}: {group_title}", file=sys.stderr)
        return 2

    data = load_toml(approvals_path)
    approvals = data.setdefault("approval", [])
    if any(a.get("group") == group_title and a.get("decision") == "approved" for a in approvals) and not args.force:
        print(f"error: group already approved: {group_title}", file=sys.stderr)
        print("use --force to append another approval record", file=sys.stderr)
        return 2

    approvals.append(
        {
            "group": group_title,
            "date": str(date.today()),
            "by": args.by,
            "decision": "approved",
            "review_note": args.review_note,
        }
    )
    approvals_path.write_text(dump_toml(data), encoding="utf-8")
    print(f"approved: {group_title}")
    print(f"by: {args.by}")
    print(f"wrote: {approvals_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
