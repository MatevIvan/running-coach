#!/usr/bin/env python3
"""Read date-bounded GarminDB recovery data without exposing credentials or routes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sqlite3
from typing import Any


SOURCE_SPECS = {
    "sleep": (
        "garmin.db",
        "sleep",
        "day",
        (
            "day",
            "start",
            "end",
            "total_sleep",
            "deep_sleep",
            "light_sleep",
            "rem_sleep",
            "awake",
            "avg_spo2",
            "avg_rr",
            "avg_stress",
            "score",
            "qualifier",
        ),
    ),
    "resting_hr": (
        "garmin.db",
        "resting_hr",
        "day",
        ("day", "resting_heart_rate"),
    ),
    "hrv": (
        "garmin.db",
        "hrv",
        "day",
        (
            "day",
            "weekly_avg",
            "last_night_avg",
            "last_night_5min_high",
            "baseline_low",
            "baseline_upper",
            "status",
        ),
    ),
    "daily_summary": (
        "garmin.db",
        "daily_summary",
        "day",
        (
            "day",
            "hr_min",
            "hr_max",
            "rhr",
            "stress_avg",
            "steps",
            "moderate_activity_time",
            "vigorous_activity_time",
            "bb_charged",
            "bb_max",
            "bb_min",
            "description",
        ),
    ),
    "derived_daily_summary": (
        "garmin_summary.db",
        "days_summary",
        "day",
        (
            "day",
            "hr_avg",
            "hr_min",
            "hr_max",
            "rhr_avg",
            "intensity_time",
            "steps",
            "sleep_avg",
            "rem_sleep_avg",
            "stress_avg",
            "activities",
            "activities_distance",
            "bb_max",
            "bb_min",
        ),
    ),
    "monitoring_hrv_status": (
        "garmin_monitoring.db",
        "monitoring_hrv_status",
        "timestamp",
        (
            "timestamp",
            "weekly_average",
            "last_night",
            "last_night_average",
            "baseline_low",
            "baseline_high",
            "status",
            "reading_count",
        ),
    ),
}


def parse_iso_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD") from error


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {str(row[1]) for row in rows}


def read_source(
    db_path: Path,
    table: str,
    date_column: str,
    requested_columns: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "database_exists": db_path.is_file(),
        "table_exists": False,
        "latest_available_date": None,
        "rows": [],
    }
    if not db_path.is_file():
        return result

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?",
            (table,),
        ).fetchone()
        if not table_exists:
            return result
        result["table_exists"] = True

        columns = table_columns(connection, table)
        if date_column not in columns:
            result["error"] = f"date column {date_column!r} is unavailable"
            return result
        selected = [column for column in requested_columns if column in columns]
        if date_column not in selected:
            selected.insert(0, date_column)

        select_sql = ", ".join(f'"{column}"' for column in selected)
        result["rows"] = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT {select_sql}
                FROM "{table}"
                WHERE date("{date_column}") BETWEEN ? AND ?
                ORDER BY datetime("{date_column}") ASC
                """,
                (start_date, end_date),
            ).fetchall()
        ]
        latest = connection.execute(
            f'SELECT MAX(date("{date_column}")) FROM "{table}"'
        ).fetchone()
        result["latest_available_date"] = latest[0] if latest else None
    finally:
        connection.close()
    return result


def requested_dates(start: dt.date, end: dt.date) -> list[str]:
    days = (end - start).days
    return [(start + dt.timedelta(days=offset)).isoformat() for offset in range(days + 1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--date", type=parse_iso_date)
    parser.add_argument("--start-date", type=parse_iso_date)
    parser.add_argument("--end-date", type=parse_iso_date)
    args = parser.parse_args()

    if args.date and (args.start_date or args.end_date):
        parser.error("--date cannot be combined with --start-date or --end-date")
    if args.date:
        start = end = args.date
    else:
        if not args.start_date or not args.end_date:
            parser.error("supply --date or both --start-date and --end-date")
        start, end = args.start_date, args.end_date
    if start > end:
        parser.error("start date cannot be after end date")
    if (end - start).days > 31:
        parser.error("date range cannot exceed 32 calendar days")

    root = args.project_root.expanduser().resolve()
    db_dir = root / "docs" / "garmindb" / "data" / "DBs"
    start_text, end_text = start.isoformat(), end.isoformat()
    sources: dict[str, Any] = {}
    for name, (db_name, table, date_column, columns) in SOURCE_SPECS.items():
        sources[name] = read_source(
            db_dir / db_name,
            table,
            date_column,
            columns,
            start_text,
            end_text,
        )

    coverage: dict[str, dict[str, bool]] = {}
    for day in requested_dates(start, end):
        coverage[day] = {}
        for name, source in sources.items():
            coverage[day][name] = any(
                str(row.get(SOURCE_SPECS[name][2], "")).startswith(day)
                for row in source["rows"]
            )

    output = {
        "requested_start_date": start_text,
        "requested_end_date": end_text,
        "database_directory_exists": db_dir.is_dir(),
        "coverage": coverage,
        "sources": sources,
        "not_guaranteed_by_garmindb": [
            "training_readiness",
            "pain",
            "soreness",
            "illness",
            "perceived_fatigue",
            "sleep_disruptions",
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
