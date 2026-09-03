#!/usr/bin/env python3
"""Create the ignored private workspace without overwriting existing data."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


PRIVATE_DIRS = (
    "activities",
    "imports",
    "screenshots",
    "athlete_reports",
)

TEMPLATE_FILES = (
    "runner_profile.md",
    "running_plan.md",
    "recovery_metrics.md",
)

LEGACY_PLAN_NAME = "marathon_plan.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create private running-project files without overwriting existing data."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing AGENTS.md (default: current directory).",
    )
    parser.add_argument(
        "--with-garmindb",
        action="store_true",
        help="Also create the private docs/garmindb working directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be created without changing files.",
    )
    return parser.parse_args()


def require_project(root: Path) -> None:
    if not (root / "AGENTS.md").is_file():
        raise RuntimeError(f"AGENTS.md was not found under project root: {root}")


def require_docs_ignored(root: Path) -> None:
    probe = Path("docs") / ".privacy-check"
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(probe)],
            cwd=root,
            check=False,
        )
        if result.returncode == 0:
            return
        raise RuntimeError(
            "Git does not ignore docs/. Add /docs/ to .gitignore before initialization."
        )

    ignore_file = root / ".gitignore"
    patterns = set()
    if ignore_file.is_file():
        patterns = {
            line.strip()
            for line in ignore_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    if not patterns.intersection({"/docs/", "/docs", "docs/", "docs"}):
        raise RuntimeError(
            "The project is not a Git repository and .gitignore does not explicitly ignore docs/."
        )


def set_private_mode(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    skill_root = Path(__file__).resolve().parent.parent
    template_dir = skill_root / "assets" / "private-workspace"

    try:
        require_project(root)
        require_docs_ignored(root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    missing_templates = [
        name for name in TEMPLATE_FILES if not (template_dir / name).is_file()
    ]
    if missing_templates:
        print(
            f"ERROR: Missing private workspace templates: {', '.join(missing_templates)}",
            file=sys.stderr,
        )
        return 2

    docs = root / "docs"
    directories = [docs, *(docs / name for name in PRIVATE_DIRS)]
    if args.with_garmindb:
        directories.append(docs / "garmindb")

    for directory in directories:
        if directory.exists():
            if not directory.is_dir():
                print(
                    f"ERROR: Expected a directory but found another file type: {directory}",
                    file=sys.stderr,
                )
                return 2
            print(f"PRESERVE directory {directory.relative_to(root)}")
            continue
        print(f"{'WOULD CREATE' if args.dry_run else 'CREATE'} directory {directory.relative_to(root)}")
        if not args.dry_run:
            directory.mkdir(parents=True, exist_ok=False)
            set_private_mode(directory, 0o700)

    legacy_plan = docs / LEGACY_PLAN_NAME
    running_plan = docs / "running_plan.md"
    legacy_plan_supplies_running_plan = legacy_plan.is_file() and not running_plan.exists()
    if legacy_plan_supplies_running_plan:
        print(
            f"{'WOULD MIGRATE' if args.dry_run else 'MIGRATE'} legacy file "
            f"{legacy_plan.relative_to(root)} to {running_plan.relative_to(root)}"
        )
        if not args.dry_run:
            shutil.copyfile(legacy_plan, running_plan)
            set_private_mode(running_plan, 0o600)
        print(
            f"PRESERVE legacy file {legacy_plan.relative_to(root)}; "
            "remove it only after verifying the migrated running plan"
        )

    for name in TEMPLATE_FILES:
        destination = docs / name
        if (
            args.dry_run
            and name == "running_plan.md"
            and legacy_plan_supplies_running_plan
        ):
            continue
        if destination.exists():
            if not destination.is_file():
                print(
                    f"ERROR: Expected a file but found another file type: {destination}",
                    file=sys.stderr,
                )
                return 2
            print(f"PRESERVE file {destination.relative_to(root)}")
            continue
        print(f"{'WOULD CREATE' if args.dry_run else 'CREATE'} file {destination.relative_to(root)}")
        if not args.dry_run:
            shutil.copyfile(template_dir / name, destination)
            set_private_mode(destination, 0o600)

    database = docs / "running_data.db"
    manager = root / ".agents" / "scripts" / "manage_running_data.py"
    if args.dry_run:
        print(f"{'PRESERVE' if database.exists() else 'WOULD CREATE'} database {database.relative_to(root)}")
    elif not manager.is_file():
        print(f"ERROR: Running-data manager not found: {manager}", file=sys.stderr)
        return 2
    else:
        result = subprocess.run(
            [sys.executable, str(manager), "--project-root", str(root), "init"],
            cwd=root,
            check=False,
        )
        if result.returncode != 0:
            print("ERROR: Could not initialize docs/running_data.db.", file=sys.stderr)
            return result.returncode
        set_private_mode(database, 0o600)

    print("Private workspace initialization complete." if not args.dry_run else "Dry run complete.")
    if os.name == "nt" and not args.dry_run:
        print(
            "NOTICE: Windows file permissions are inherited from the containing folder; "
            "keep docs/ in a private user-owned location and review its ACL if the computer "
            "or workspace is shared."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
