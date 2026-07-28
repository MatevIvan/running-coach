#!/usr/bin/env python3
"""Run a guarded GarminDB recovery sync and verify prior-day coverage."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


REQUIRED_STATS = ("monitoring", "sleep", "rhr", "hrv")
REQUIRED_COVERAGE = ("sleep", "resting_hr", "hrv", "daily_summary")


def parse_iso_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD") from error


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def find_cli(root: Path) -> Path | None:
    candidates = [
        root / ".venv" / "bin" / "garmindb_cli.py",
        root / ".venv" / "Scripts" / "garmindb_cli.py",
        root / ".venv" / "Scripts" / "garmindb_cli.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def inspect_config(config_path: Path) -> None:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"GarminDB config is unreadable: {config_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"GarminDB config is not valid JSON: {config_path}") from error

    if not isinstance(config, dict):
        raise ValueError("GarminDB config must contain a JSON object.")
    enabled = config.get("enabled_stats", {})
    missing = [name for name in REQUIRED_STATS if enabled.get(name) is not True]
    if missing:
        raise ValueError(
            "GarminDB recovery sources are not enabled in the private config: "
            + ", ".join(missing)
            + "."
        )


def database_is_healthy(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()
    finally:
        connection.close()
    return bool(result and result[0] == "ok")


def classify_failure(output: str) -> tuple[str, str]:
    lowered = output.lower()
    if any(term in lowered for term in ("mfa", "multi-factor", "two-factor")):
        return (
            "mfa",
            "Garmin authentication requires an interactive MFA step; prior-day recovery was not refreshed.",
        )
    if any(
        term in lowered
        for term in (
            "failed to login",
            "login failed",
            "authentication",
            "unauthorized",
            "retrieve social profile",
            "401",
        )
    ):
        return (
            "authentication",
            "GarminDB could not authenticate with Garmin Connect; prior-day recovery was not refreshed.",
        )
    if any(
        term in lowered
        for term in (
            "name or service not known",
            "network is unreachable",
            "connection refused",
            "connection reset",
            "could not resolve",
            "timed out",
            "timeout",
        )
    ):
        return (
            "network",
            "GarminDB could not reach Garmin Connect; prior-day recovery was not refreshed.",
        )
    if "database is locked" in lowered:
        return (
            "database_locked",
            "A GarminDB database is locked, possibly by another sync; prior-day recovery was not refreshed.",
        )
    return (
        "garmindb",
        "GarminDB returned an error; prior-day recovery was not refreshed.",
    )


@contextmanager
def sync_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        if os.name == "posix":
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("Another GarminDB sync is already running.") from error
        else:
            import msvcrt

            handle.seek(0)
            if not handle.read(1):
                handle.write("0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Another GarminDB sync is already running.") from error
        yield
    finally:
        if os.name == "posix":
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        else:
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        handle.close()


def read_daily(reader_path: Path, root: Path, target_date: dt.date) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(reader_path),
            "--project-root",
            str(root),
            "--date",
            target_date.isoformat(),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Prior-day coverage reader failed: {message}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Prior-day coverage reader returned invalid JSON.") from error
    if not isinstance(result, dict):
        raise RuntimeError("Prior-day coverage reader returned an invalid result.")
    return result


def coverage_for(data: dict[str, Any], target_date: str) -> dict[str, bool]:
    coverage = data.get("coverage", {}).get(target_date, {})
    return {name: bool(coverage.get(name)) for name in REQUIRED_COVERAGE}


def body_battery_available(data: dict[str, Any]) -> bool:
    rows = data.get("sources", {}).get("daily_summary", {}).get("rows", [])
    return any(
        any(row.get(field) is not None for field in ("bb_charged", "bb_max", "bb_min"))
        for row in rows
        if isinstance(row, dict)
    )


def emit(result: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"Status: {result['status']}")
    print(result["message"])
    if result.get("category"):
        print(f"Category: {result['category']}")
    if result.get("target_date"):
        print(f"Verified date: {result['target_date']}")
    if result.get("log"):
        print(f"Private log: {result['log']}")


def fail(
    status: str,
    category: str,
    message: str,
    as_json: bool,
    exit_code: int,
    target_date: str | None = None,
    log_path: str | None = None,
) -> int:
    result: dict[str, object] = {
        "status": status,
        "category": category,
        "message": message,
        "sync_completed": False,
        "fresh_data_imported": False,
    }
    if target_date:
        result["target_date"] = target_date
    if log_path:
        result["log"] = log_path
    emit(result, as_json)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync GarminDB recovery data through yesterday and verify exact-date coverage."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--date",
        type=parse_iso_date,
        help="Prior date to verify; defaults to yesterday.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    today = dt.date.today()
    target_date = args.date or today - dt.timedelta(days=1)
    target_text = target_date.isoformat()
    if target_date >= today:
        parser.error("--date must be earlier than today; current-day sleep is user supplied")

    root = args.project_root.expanduser().resolve()
    working_dir = root / "docs" / "garmindb"
    config_path = working_dir / "GarminConnectConfig.json"
    data_dir = working_dir / "data"
    db_path = data_dir / "DBs" / "garmin.db"
    log_path = working_dir / "garmindb.log"
    reader_path = (
        root
        / ".agents"
        / "skills"
        / "collect-daily-metrics"
        / "scripts"
        / "read_garmindb_daily.py"
    )
    cli_path = find_cli(root)

    missing = [
        relative_path(path, root)
        for path in (config_path, data_dir, reader_path)
        if not path.exists()
    ]
    if cli_path is None:
        missing.append(".venv GarminDB CLI")
    if missing:
        return fail(
            "not_connected",
            "preflight",
            f"GarminDB is not connected; missing: {', '.join(missing)}.",
            args.json,
            2,
            target_text,
        )

    try:
        inspect_config(config_path)
    except ValueError as error:
        return fail("failed", "config", str(error), args.json, 3, target_text)

    if args.dry_run:
        emit(
            {
                "status": "ready",
                "message": (
                    "GarminDB recovery sync preflight passed; no network command was run."
                ),
                "sync_completed": False,
                "fresh_data_imported": False,
                "target_date": target_text,
                "working_directory": relative_path(working_dir, root),
                "database": relative_path(db_path, root),
            },
            args.json,
        )
        return 0

    try:
        before = read_daily(reader_path, root, target_date)
    except RuntimeError:
        before = {}

    command = [
        str(cli_path),
        "--config",
        ".",
        "--monitoring",
        "--sleep",
        "--rhr",
        "--hrv",
        "--download",
        "--import",
        "--analyze",
        "--latest",
    ]

    try:
        with sync_lock(working_dir / ".garmindb_sync.lock"):
            completed = subprocess.run(
                command,
                cwd=working_dir,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
    except RuntimeError as error:
        return fail("busy", "lock", str(error), args.json, 5, target_text)
    except OSError as error:
        return fail(
            "failed",
            "process",
            f"Could not start GarminDB: {error}.",
            args.json,
            6,
            target_text,
        )

    private_log = relative_path(log_path, root)
    if completed.returncode != 0:
        category, message = classify_failure(completed.stdout or "")
        return fail(
            "failed",
            category,
            message,
            args.json,
            10,
            target_text,
            private_log,
        )

    try:
        if not database_is_healthy(db_path):
            return fail(
                "failed",
                "verification",
                "GarminDB exited successfully, but garmin.db did not pass verification.",
                args.json,
                11,
                target_text,
                private_log,
            )
        after = read_daily(reader_path, root, target_date)
    except (sqlite3.Error, RuntimeError) as error:
        return fail(
            "failed",
            "verification",
            f"GarminDB exited successfully, but prior-day verification failed: {error}.",
            args.json,
            11,
            target_text,
            private_log,
        )

    coverage = coverage_for(after, target_text)
    body_battery = body_battery_available(after)
    missing_sources = [name for name, present in coverage.items() if not present]
    if not body_battery:
        missing_sources.append("body_battery")
    coverage_complete = not missing_sources
    fresh_data = bool(after != before)
    emit(
        {
            "status": "success",
            "message": (
                "GarminDB recovery sync completed and prior-day sleep and Body Battery are available."
                if coverage_complete
                else "GarminDB recovery sync completed, but some prior-day recovery fields remain unavailable."
            ),
            "sync_completed": True,
            "fresh_data_imported": fresh_data,
            "target_date": target_text,
            "coverage": coverage,
            "body_battery_available": body_battery,
            "coverage_complete": coverage_complete,
            "missing_sources": missing_sources,
            "database_verified": True,
            "log": private_log,
        },
        args.json,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
