#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        check=check,
    )


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")
    if not slug:
        raise SystemExit("experiment name must contain at least one alphanumeric character")
    return slug.lower()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path) -> None:
    ensure_parent(dst)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def validate_relative_dir(path_str: str, expected_prefix: str) -> Path:
    path = (ROOT / path_str).resolve()
    try:
        rel = path.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit(f"path escapes repository root: {path_str}") from exc
    if rel.parts[: len(Path(expected_prefix).parts)] != Path(expected_prefix).parts:
        raise SystemExit(f"path must be under {expected_prefix}: {path_str}")
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"directory does not exist: {path_str}")
    return path


def snapshot_git_context(archive_dir: Path) -> None:
    git_dir = archive_dir / "git"
    git_dir.mkdir(parents=True, exist_ok=True)

    root_info = {
        "head": run(["git", "rev-parse", "HEAD"]).stdout.strip(),
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip(),
    }
    (git_dir / "root.json").write_text(json.dumps(root_info, indent=2) + "\n")
    (git_dir / "status.txt").write_text(run(["git", "status", "--short", "--branch"]).stdout)
    (git_dir / "submodule_status.txt").write_text(run(["git", "submodule", "status"]).stdout)

    software = ROOT / "software"
    repos: list[dict[str, str]] = []
    if software.exists():
        for child in sorted(software.iterdir()):
            if not child.is_dir() or not (child / ".git").exists():
                continue
            try:
                head = run(["git", "rev-parse", "HEAD"], cwd=child).stdout.strip()
                branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=child).stdout.strip()
                status = run(["git", "status", "--short", "--branch"], cwd=child).stdout
            except subprocess.CalledProcessError as exc:
                status = exc.stdout + exc.stderr
                head = ""
                branch = ""
            repos.append(
                {
                    "path": str(child.relative_to(ROOT)),
                    "head": head,
                    "branch": branch,
                    "status": status,
                }
            )
    (git_dir / "software_repos.json").write_text(json.dumps(repos, indent=2) + "\n")


def create_or_checkout_branch(repo: Path, branch: str) -> str:
    existing = run(["git", "branch", "--list", branch], cwd=repo).stdout.strip()
    if existing:
        run(["git", "checkout", branch], cwd=repo)
        return "checked_out_existing"
    run(["git", "checkout", "-b", branch], cwd=repo)
    return "created"


def current_branch(repo: Path) -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo).stdout.strip()


def clean_path(repo: Path, relpath: Path) -> None:
    run(["git", "checkout", "--", str(relpath)], cwd=repo, check=False)
    run(["git", "clean", "-fd", "--", str(relpath)], cwd=repo, check=False)


def submodule_excludes(repo: Path) -> list[str]:
    rel = str(repo.relative_to(ROOT))
    if rel == "software/mcfm":
        return ["Bin", "install"]
    return []


def drop_excluded_paths_from_worktree(repo: Path, excludes: list[str]) -> None:
    for path in excludes:
        run(["git", "restore", "--staged", "--worktree", "--", path], cwd=repo, check=False)
        run(["git", "clean", "-fd", "--", path], cwd=repo, check=False)


def copy_loop_artifacts(loop_dir: Path, archive_dir: Path) -> None:
    files = [
        "logs/toolusage.toml",
        "loop/run.toml",
        "loop/author.toml",
        "loop/review.toml",
        "loop/review_output.toml",
        "loop/state.toml",
    ]
    for rel in files:
        src = loop_dir / rel
        if src.exists():
            copy_file(src, archive_dir / rel)

    metadata = loop_dir / "loop" / "metadata"
    if metadata.exists() and metadata.is_dir():
        copy_tree(metadata, archive_dir / "loop" / "metadata")


def commit_submodule(repo: Path, branch: str, message: str) -> dict[str, object]:
    action = create_or_checkout_branch(repo, branch)
    excludes = submodule_excludes(repo)
    run(["git", "add", "-A"], cwd=repo)
    drop_excluded_paths_from_worktree(repo, excludes)
    status = run(["git", "status", "--short"], cwd=repo).stdout.strip()
    info: dict[str, object] = {
        "repo": str(repo.relative_to(ROOT)),
        "branch": current_branch(repo),
        "branch_action": action,
        "excluded_paths": excludes,
        "committed": False,
    }
    if not status:
        info["note"] = "nothing to commit"
        return info
    run(["git", "commit", "-m", message], cwd=repo)
    info["committed"] = True
    info["head"] = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    return info


def write_summary(
    archive_dir: Path,
    experiment_name: str,
    loop_dir: Path,
    transformation_dir: Path,
    submodules: list[Path],
    branch: str,
    submodule_results: list[dict[str, object]],
    included_dev_tmp: bool,
    cleanup_performed: bool,
) -> None:
    summary = {
        "experiment_name": experiment_name,
        "archive_created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "loop_source": str(loop_dir.relative_to(ROOT)),
        "transformation_source": str(transformation_dir.relative_to(ROOT)),
        "submodules": [str(path.relative_to(ROOT)) for path in submodules],
        "archive_branch": branch,
        "submodule_results": submodule_results,
        "included_dev_tmp": included_dev_tmp,
        "cleanup_performed": cleanup_performed,
    }
    (archive_dir / "archive_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic archive tool for eval experiments.")
    parser.add_argument("experiment_name", help="user-provided experiment name")
    parser.add_argument("--transformation", required=True, help="path like dev/transformations/<name>")
    parser.add_argument("--loop-dir", required=True, help="path like .csloop or .codescribe")
    parser.add_argument("--submodule", action="append", default=[], help="path like software/<name>; may be repeated")
    parser.add_argument("--include-dev-tmp", action="store_true", help="copy dev/tmp into archive")
    args = parser.parse_args()

    experiment = slugify(args.experiment_name)
    transformation_dir = validate_relative_dir(args.transformation, "dev/transformations")
    loop_dir = validate_relative_dir(args.loop_dir, ".")
    if loop_dir.name not in {".csloop", ".codescribe"}:
        raise SystemExit("--loop-dir must point to .csloop or .codescribe")
    submodules = [validate_relative_dir(path, "software") for path in args.submodule]

    date_dir = dt.datetime.now().strftime("%m-%d-%Y")
    archive_dir = ROOT / "evals" / "experiments" / date_dir / experiment
    archive_dir.mkdir(parents=True, exist_ok=True)

    copy_tree(transformation_dir, archive_dir / transformation_dir.relative_to(ROOT))
    copy_loop_artifacts(loop_dir, archive_dir)
    if args.include_dev_tmp:
        dev_tmp = ROOT / "dev" / "tmp"
        if dev_tmp.exists() and dev_tmp.is_dir():
            copy_tree(dev_tmp, archive_dir / "dev" / "tmp")
    snapshot_git_context(archive_dir)

    branch = f"evals/{date_dir}/{experiment}"
    submodule_results: list[dict[str, object]] = []
    for submodule in submodules:
        if not (submodule / ".git").exists():
            raise SystemExit(f"submodule is not a git repo: {submodule.relative_to(ROOT)}")
        submodule_results.append(commit_submodule(submodule, branch, f"Archive experiment {experiment}"))

    clean_path(ROOT, transformation_dir.relative_to(ROOT))
    clean_path(ROOT, loop_dir.relative_to(ROOT))
    cleanup_performed = True

    write_summary(
        archive_dir,
        experiment,
        loop_dir,
        transformation_dir,
        submodules,
        branch,
        submodule_results,
        args.include_dev_tmp,
        cleanup_performed,
    )

    print(f"Archived experiment to {archive_dir.relative_to(ROOT)}")
    for result in submodule_results:
        if result.get("committed"):
            print(f"{result['repo']}: on {result['branch']}, committed {result['head']}")
        else:
            print(f"{result['repo']}: on {result['branch']}, {result['note']}")
    print(f"Cleaned {transformation_dir.relative_to(ROOT)}")
    print(f"Cleaned {loop_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
