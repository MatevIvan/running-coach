#!/usr/bin/env python3
"""Create or validate a private GarminDB configuration without exposing secrets."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing AGENTS.md (default: current directory).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a new private config.")
    create.add_argument("--start-date", required=True, help="Earliest date as YYYY-MM-DD.")
    create.add_argument("--activity-count", required=True, type=int)
    create.add_argument("--latest-activity-count", default=25, type=int)
    create.add_argument("--units", choices=("metric", "statute"), default="statute")
    create.add_argument(
        "--credential-mode",
        choices=("config", "password-file", "macos-keychain"),
        default="password-file",
    )
    create.add_argument(
        "--mount-dir",
        help=(
            "Optional mounted Garmin-device directory. Online Garmin Connect imports "
            "do not require this path."
        ),
    )
    create.add_argument("--enable-weight", action="store_true")

    subparsers.add_parser("validate", help="Validate config without printing credentials.")
    return parser


def docs_are_ignored(root: Path) -> bool:
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", "docs/.privacy-check"],
            cwd=root,
            check=False,
        )
        return result.returncode == 0
    ignore_file = root / ".gitignore"
    if not ignore_file.is_file():
        return False
    patterns = {
        line.strip()
        for line in ignore_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return bool(patterns.intersection({"/docs/", "/docs", "docs/", "docs"}))


def parse_start_date(value: str) -> str:
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("--start-date must use YYYY-MM-DD.") from exc
    if parsed > dt.date.today():
        raise ValueError("--start-date cannot be in the future.")
    return parsed.strftime("%m/%d/%Y")


def within_private_docs(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((path.resolve(), (root / "docs").resolve())) == str(
            (root / "docs").resolve()
        )
    except ValueError:
        return False


def create_config(args: argparse.Namespace, root: Path) -> int:
    if args.activity_count < 1 or args.activity_count > 100_000:
        raise ValueError("--activity-count must be between 1 and 100000.")
    if args.latest_activity_count < 1 or args.latest_activity_count > 1_000:
        raise ValueError("--latest-activity-count must be between 1 and 1000.")
    if args.credential_mode == "macos-keychain" and platform.system() != "Darwin":
        raise ValueError("macos-keychain credential mode is available only on macOS.")

    start_date = parse_start_date(args.start_date)
    working_dir = root / "docs" / "garmindb"
    config_path = working_dir / "GarminConnectConfig.json"
    data_dir = working_dir / "data"
    password_file = working_dir / ".garmin_password"
    if args.mount_dir:
        mount_dir = str(Path(args.mount_dir).expanduser().resolve())
    elif platform.system() == "Darwin":
        mount_dir = "/Volumes/GARMIN"
    else:
        mount_dir = str(working_dir / "device_mount")

    working_dir.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        print(f"ERROR: Preserve existing config; not overwritten: {config_path}", file=sys.stderr)
        return 3

    credential_config: dict[str, Any] = {
        "user": "",
        "secure_password": args.credential_mode == "macos-keychain",
        "password": "",
        "password_file": (
            str(password_file) if args.credential_mode == "password-file" else None
        ),
    }

    config = {
        "db": {"type": "sqlite"},
        "garmin": {"domain": "garmin.com"},
        "credentials": credential_config,
        "data": {
            "weight_start_date": start_date,
            "sleep_start_date": start_date,
            "rhr_start_date": start_date,
            "hrv_start_date": start_date,
            "monitoring_start_date": start_date,
            "download_latest_activities": args.latest_activity_count,
            "download_all_activities": args.activity_count,
        },
        "directories": {
            "relative_to_home": False,
            "base_dir": str(data_dir),
            "mount_dir": mount_dir,
        },
        "enabled_stats": {
            "monitoring": True,
            "steps": True,
            "itime": True,
            "sleep": True,
            "rhr": True,
            "hrv": True,
            "weight": args.enable_weight,
            "activities": True,
        },
        "course_views": {"steps": []},
        "modes": {},
        "activities": {"display": []},
        "settings": {
            "metric": args.units == "metric",
            "default_display_activities": ["walking", "running", "cycling"],
        },
        "checkup": {"look_back_days": 90},
    }

    with config_path.open("x", encoding="utf-8") as output:
        json.dump(config, output, indent=4)
        output.write("\n")
    try:
        os.chmod(config_path, 0o600)
    except OSError:
        pass

    if args.credential_mode == "password-file":
        if not password_file.exists():
            password_file.touch(mode=0o600)
        print(f"Created private password file: {password_file}")

    print(f"Created GarminDB config: {config_path}")
    print(f"GarminDB data directory: {data_dir}")
    if os.name == "nt":
        print(
            "NOTICE: Windows file permissions are inherited from the containing folder; "
            "keep docs/ in a private user-owned location and review its ACL if the computer "
            "or workspace is shared."
        )
    print("Credentials remain incomplete; edit them locally before validation or download.")
    return 0


def load_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open(encoding="utf-8") as source:
            config = json.load(source)
    except FileNotFoundError as exc:
        raise ValueError(f"Config does not exist: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Config is not valid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("Config root must be a JSON object.")
    return config


def validate_config(root: Path) -> int:
    config_path = root / "docs" / "garmindb" / "GarminConnectConfig.json"
    config = load_config(config_path)
    errors: list[str] = []

    credentials = config.get("credentials", {})
    user = credentials.get("user")
    if not isinstance(user, str) or not user.strip() or "REPLACE_WITH" in user:
        errors.append("credentials.user is missing.")

    if credentials.get("secure_password"):
        if platform.system() != "Darwin":
            errors.append("secure_password is enabled outside macOS.")
        else:
            result = subprocess.run(
                ["security", "find-internet-password", "-s", "sso.garmin.com", "-w"],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                errors.append("No sso.garmin.com Internet Password was found in the macOS Login Keychain.")
    elif credentials.get("password_file"):
        password_path = Path(str(credentials["password_file"])).expanduser()
        if not within_private_docs(password_path, root):
            errors.append("credentials.password_file must remain under docs/.")
        elif not password_path.is_file() or password_path.stat().st_size == 0:
            errors.append("The configured private password file is missing or empty.")
    else:
        password = credentials.get("password")
        if not isinstance(password, str) or not password or "REPLACE_WITH" in password:
            errors.append("credentials.password is missing.")

    directories = config.get("directories", {})
    base_dir = Path(str(directories.get("base_dir", ""))).expanduser()
    if not str(base_dir) or not within_private_docs(base_dir, root):
        errors.append("directories.base_dir must point under this project's docs/.")

    data = config.get("data", {})
    for key in (
        "weight_start_date",
        "sleep_start_date",
        "rhr_start_date",
        "hrv_start_date",
        "monitoring_start_date",
    ):
        try:
            dt.datetime.strptime(str(data.get(key, "")), "%m/%d/%Y")
        except ValueError:
            errors.append(f"data.{key} must use MM/DD/YYYY.")

    if errors:
        print("GarminDB configuration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print("GarminDB configuration is valid; credential values were not displayed.")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if not (root / "AGENTS.md").is_file():
        print(f"ERROR: AGENTS.md not found under project root: {root}", file=sys.stderr)
        return 2
    if not docs_are_ignored(root):
        print("ERROR: Git does not ignore docs/. Fix .gitignore first.", file=sys.stderr)
        return 2

    try:
        if args.command == "create":
            return create_config(args, root)
        return validate_config(root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
