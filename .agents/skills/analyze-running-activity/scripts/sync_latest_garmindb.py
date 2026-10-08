#!/usr/bin/env python3
"""Run a guarded incremental GarminDB activity sync."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator


DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_INITIAL_BACKOFF_SECONDS = 2.0
DEFAULT_MAX_BACKOFF_SECONDS = 30.0


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def find_cli_command(root: Path) -> list[str] | None:
    script_candidates = (
        (
            root / ".venv" / "bin" / "python",
            root / ".venv" / "bin" / "garmindb_cli.py",
        ),
        (
            root / ".venv" / "Scripts" / "python.exe",
            root / ".venv" / "Scripts" / "garmindb_cli.py",
        ),
    )
    for interpreter, script in script_candidates:
        if interpreter.is_file() and script.is_file():
            return [str(interpreter), str(script)]

    executable_candidates = (
        root / ".venv" / "Scripts" / "garmindb_cli.exe",
        root / ".venv" / "Scripts" / "garmindb_cli.py.exe",
    )
    for executable in executable_candidates:
        if executable.is_file():
            return [str(executable)]
    return None


def inspect_config(config_path: Path) -> None:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"GarminDB config is unreadable: {config_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"GarminDB config is not valid JSON: {config_path}") from error

    if not isinstance(config, dict):
        raise ValueError("GarminDB config must contain a JSON object.")
    if config.get("enabled_stats", {}).get("activities") is not True:
        raise ValueError("GarminDB activities are not enabled in the private config.")


def latest_activity(db_path: Path) -> dict[str, object] | None:
    if not db_path.is_file():
        return None
    connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            """
            SELECT activity_id, start_time
            FROM activities
            ORDER BY datetime(start_time) DESC, activity_id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()
    return dict(row) if row else None


def database_is_healthy(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()
    finally:
        connection.close()
    return bool(result and result[0] == "ok")


def log_size(log_path: Path) -> int:
    try:
        return log_path.stat().st_size
    except OSError:
        return 0


def read_log_delta(log_path: Path, start: int) -> str:
    try:
        with log_path.open("rb") as handle:
            if handle.seek(0, os.SEEK_END) < start:
                start = 0
            handle.seek(start)
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def has_terminal_failure(output: str) -> bool:
    lowered = output.lower()
    return any(
        term in lowered
        for term in (
            "failed to login!",
            "all login strategies exhausted",
            "error:root:login failed",
        )
    )


def classify_failure(output: str) -> tuple[str, str]:
    lowered = output.lower()
    if any(term in lowered for term in ("mfa", "multi-factor", "two-factor")):
        return (
            "mfa",
            "Garmin authentication requires an interactive MFA step; no fresh data was imported.",
        )
    if any(
        term in lowered
        for term in (
            "name or service not known",
            "name resolution",
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
            "GarminDB could not reach Garmin Connect; no fresh data was imported.",
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
            "GarminDB could not authenticate with Garmin Connect; no fresh data was imported.",
        )
    if "database is locked" in lowered:
        return (
            "database_locked",
            "A GarminDB database is locked, possibly by another import; no fresh data was confirmed.",
        )
    return (
        "garmindb",
        "GarminDB returned an error; no fresh data was confirmed.",
    )


def backoff_delay(
    retry_number: int,
    initial_seconds: float,
    maximum_seconds: float,
) -> float:
    """Return a bounded exponential delay for a one-based retry number."""
    if retry_number < 1:
        raise ValueError("retry_number must be at least 1")
    return min(initial_seconds * (2 ** (retry_number - 1)), maximum_seconds)


def run_with_network_backoff(
    command: list[str],
    working_dir: Path,
    log_path: Path,
    max_attempts: int,
    initial_backoff_seconds: float,
    max_backoff_seconds: float,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[subprocess.CompletedProcess[str], str, int, list[float]]:
    """Run GarminDB, retrying only failures classified as transient network errors."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if initial_backoff_seconds <= 0 or max_backoff_seconds <= 0:
        raise ValueError("backoff delays must be greater than zero")

    retry_delays: list[float] = []
    for attempt in range(1, max_attempts + 1):
        log_start = log_size(log_path)
        completed = runner(
            command,
            cwd=working_dir,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        diagnostics = "\n".join(
            part
            for part in (
                completed.stdout or "",
                read_log_delta(log_path, log_start),
            )
            if part
        )
        failed = completed.returncode != 0 or has_terminal_failure(diagnostics)
        if not failed:
            return completed, diagnostics, attempt, retry_delays

        category, _ = classify_failure(diagnostics)
        if category != "network" or attempt == max_attempts:
            return completed, diagnostics, attempt, retry_delays

        delay = backoff_delay(
            retry_number=attempt,
            initial_seconds=initial_backoff_seconds,
            maximum_seconds=max_backoff_seconds,
        )
        retry_delays.append(delay)
        sleeper(delay)

    raise AssertionError("GarminDB retry loop exited without a result")


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
                raise RuntimeError("Another GarminDB activity sync is already running.") from error
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
                raise RuntimeError("Another GarminDB activity sync is already running.") from error
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


def emit(result: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"Status: {result['status']}")
    print(result["message"])
    if result.get("category"):
        print(f"Category: {result['category']}")
    if result.get("log"):
        print(f"Private log: {result['log']}")


def fail(
    status: str,
    category: str,
    message: str,
    as_json: bool,
    exit_code: int,
    log_path: str | None = None,
    extra: dict[str, object] | None = None,
) -> int:
    result: dict[str, object] = {
        "status": status,
        "category": category,
        "message": message,
        "sync_completed": False,
        "fresh_data_imported": False,
    }
    if log_path:
        result["log"] = log_path
    if extra:
        result.update(extra)
    emit(result, as_json)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the incremental GarminDB activity sync and verify its local database."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help="Maximum GarminDB attempts for transient network failures (default: 3).",
    )
    parser.add_argument(
        "--initial-backoff-seconds",
        type=float,
        default=DEFAULT_INITIAL_BACKOFF_SECONDS,
        help="Delay before the first network retry (default: 2 seconds).",
    )
    parser.add_argument(
        "--max-backoff-seconds",
        type=float,
        default=DEFAULT_MAX_BACKOFF_SECONDS,
        help="Maximum delay between network retries (default: 30 seconds).",
    )
    args = parser.parse_args()

    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    if args.initial_backoff_seconds <= 0:
        parser.error("--initial-backoff-seconds must be greater than zero")
    if args.max_backoff_seconds <= 0:
        parser.error("--max-backoff-seconds must be greater than zero")

    root = args.project_root.expanduser().resolve()
    working_dir = root / "docs" / "garmindb"
    config_path = working_dir / "GarminConnectConfig.json"
    data_dir = working_dir / "data"
    db_path = data_dir / "DBs" / "garmin_activities.db"
    log_path = working_dir / "garmindb.log"
    cli_command = find_cli_command(root)

    missing = [
        relative_path(path, root)
        for path in (config_path, data_dir)
        if not path.exists()
    ]
    if cli_command is None:
        missing.append(".venv GarminDB CLI and matching Python interpreter")
    if missing:
        return fail(
            "not_connected",
            "preflight",
            f"GarminDB is not connected; missing: {', '.join(missing)}.",
            args.json,
            2,
        )

    try:
        inspect_config(config_path)
    except ValueError as error:
        return fail("failed", "config", str(error), args.json, 3)

    command = [
        *cli_command,
        "--config",
        ".",
        "--activities",
        "--download",
        "--import",
        "--analyze",
        "--latest",
    ]

    if args.dry_run:
        emit(
            {
                "status": "ready",
                "message": "GarminDB activity sync preflight passed; no network command was run.",
                "sync_completed": False,
                "fresh_data_imported": False,
                "working_directory": relative_path(working_dir, root),
                "database": relative_path(db_path, root),
                "max_attempts": args.max_attempts,
                "initial_backoff_seconds": args.initial_backoff_seconds,
                "max_backoff_seconds": args.max_backoff_seconds,
            },
            args.json,
        )
        return 0

    try:
        before = latest_activity(db_path)
    except sqlite3.Error as error:
        return fail(
            "failed",
            "database",
            f"Could not inspect the existing activities database: {error}.",
            args.json,
            4,
        )

    try:
        with sync_lock(working_dir / ".garmindb_sync.lock"):
            completed, diagnostic_output, attempts, retry_delays = run_with_network_backoff(
                command,
                working_dir,
                log_path,
                max_attempts=args.max_attempts,
                initial_backoff_seconds=args.initial_backoff_seconds,
                max_backoff_seconds=args.max_backoff_seconds,
            )
    except RuntimeError as error:
        return fail("busy", "lock", str(error), args.json, 5)
    except OSError as error:
        return fail(
            "failed",
            "process",
            f"Could not start GarminDB: {error}.",
            args.json,
            6,
        )

    private_log = relative_path(log_path, root)
    if completed.returncode != 0 or has_terminal_failure(diagnostic_output):
        category, message = classify_failure(diagnostic_output)
        if category == "network" and attempts > 1:
            message = (
                f"GarminDB could not reach Garmin Connect after {attempts} attempts; "
                "no fresh data was imported."
            )
        return fail(
            "failed",
            category,
            message,
            args.json,
            10,
            private_log,
            {
                "attempts": attempts,
                "retry_delays_seconds": retry_delays,
            },
        )

    try:
        if not database_is_healthy(db_path):
            return fail(
                "failed",
                "verification",
                "GarminDB exited successfully, but the activities database did not pass verification.",
                args.json,
                11,
                private_log,
            )
        after = latest_activity(db_path)
    except sqlite3.Error as error:
        return fail(
            "failed",
            "verification",
            f"GarminDB exited successfully, but database verification failed: {error}.",
            args.json,
            11,
            private_log,
        )

    new_activity = bool(after and after != before)
    emit(
        {
            "status": "success",
            "message": (
                "GarminDB activity sync completed and a newer activity was found."
                if new_activity
                else "GarminDB activity sync completed; no newer activity was found."
            ),
            "sync_completed": True,
            "fresh_data_imported": new_activity,
            "database_verified": True,
            "latest_activity": after,
            "log": private_log,
            "attempts": attempts,
            "retry_delays_seconds": retry_delays,
        },
        args.json,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
