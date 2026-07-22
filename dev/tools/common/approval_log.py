"""Shared approval-log helpers for transformation workflows."""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib  # py312+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def parse_groups(log_path: Path) -> list[dict]:
    if not log_path.exists():
        raise FileNotFoundError(f"agent log not found: {log_path}")
    groups: list[dict] = []
    current: dict | None = None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("## Group") or s.startswith("### Group") or s.startswith("#### Group"):
            parts = s.split(None, 1)
            if len(parts) == 2:
                current = {"title": parts[1].strip(), "items": []}
                groups.append(current)
            continue
        if current is None:
            continue
        if s.startswith("- ["):
            current["items"].append(s)
    return groups


def item_status(item: str) -> str | None:
    marker = " — "
    if marker not in item:
        return None
    tail = item.split(marker, 1)[1]
    return tail.split(" ", 1)[0].split("(", 1)[0].strip()


def is_complete(group: dict) -> bool:
    items = group.get("items", [])
    return bool(items) and all(i.strip().startswith("- [x]") for i in items)


def is_open(group: dict) -> bool:
    items = group.get("items", [])
    return any(i.strip().startswith("- [ ]") for i in items)


def load_toml(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "approval": []}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if "approval" not in data:
        data["approval"] = []
    return data


def load_approval_records(path: Path) -> list[dict]:
    data = load_toml(path)
    records = []
    for item in data.get("approval", []):
        if item.get("group"):
            records.append(dict(item))
    return records


def approvals_for_group(path: Path, group: str) -> list[dict]:
    return [item for item in load_approval_records(path) if str(item.get("group")) == group]


def latest_approval_for_group(path: Path, group: str) -> dict | None:
    matches = approvals_for_group(path, group)
    return matches[-1] if matches else None


def latest_approved_record(path: Path) -> dict | None:
    approved = [item for item in load_approval_records(path) if item.get("decision") == "approved"]
    return approved[-1] if approved else None


def load_approved_groups(path: Path) -> set[str]:
    approved = set()
    for item in load_approval_records(path):
        if item.get("decision") == "approved" and item.get("group"):
            approved.add(str(item["group"]))
    return approved


def pending_groups(log_path: Path, approvals_path: Path) -> list[str]:
    groups = parse_groups(log_path)
    approved = load_approved_groups(approvals_path)
    return [g["title"] for g in groups if is_complete(g) and g["title"] not in approved]
