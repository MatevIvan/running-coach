#!/usr/bin/env python3
"""List recent GarminDB running activities without exposing route data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def find_fit_file(root: Path, activity_id: str) -> Path | None:
    fit_dir = root / "docs" / "garmindb" / "data" / "FitFiles" / "Activities"
    direct = fit_dir / f"{activity_id}_ACTIVITY.fit"
    if direct.is_file():
        return direct
    matches = sorted(fit_dir.glob(f"{activity_id}*.fit")) if fit_dir.is_dir() else []
    return matches[0] if matches else None


def read_units(root: Path) -> str:
    config_path = root / "docs" / "garmindb" / "GarminConnectConfig.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        metric = config.get("settings", {}).get("metric")
        if metric is True:
            return "km"
        if metric is False:
            return "mi"
        return "configured units"
    except (OSError, json.JSONDecodeError, AttributeError):
        return "configured units"


def parse_iso_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD") from error


def list_runs(
    root: Path,
    limit: int,
    exact_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, object]]:
    db_path = root / "docs" / "garmindb" / "data" / "DBs" / "garmin_activities.db"
    if not db_path.is_file():
        raise FileNotFoundError(f"GarminDB activities database not found: {db_path}")

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        conditions = ["lower(a.sport) = 'running'"]
        parameters: list[object] = []
        if exact_date:
            conditions.append("date(a.start_time) = ?")
            parameters.append(exact_date)
        elif start_date and end_date:
            conditions.append("date(a.start_time) BETWEEN ? AND ?")
            parameters.extend((start_date, end_date))
        parameters.append(limit)

        rows = connection.execute(
            f"""
            SELECT
                a.activity_id,
                a.name,
                a.start_time,
                a.elapsed_time,
                a.distance,
                a.avg_hr,
                a.max_hr,
                a.sub_sport,
                a.self_eval_feel,
                a.self_eval_effort,
                a.laps AS summary_laps,
                (SELECT COUNT(*) FROM activity_laps l WHERE l.activity_id = a.activity_id) AS lap_rows,
                (SELECT COUNT(*) FROM activity_records r WHERE r.activity_id = a.activity_id) AS record_rows,
                (SELECT COUNT(*) FROM activity_records r
                 WHERE r.activity_id = a.activity_id
                   AND r.position_lat IS NOT NULL
                   AND r.position_long IS NOT NULL) AS gps_record_rows,
                (SELECT COUNT(*) FROM activity_splits s WHERE s.activity_id = a.activity_id) AS split_rows
            FROM activities a
            WHERE {" AND ".join(conditions)}
            ORDER BY datetime(a.start_time) DESC, a.activity_id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()
    finally:
        connection.close()

    units = read_units(root)
    results = []
    for row in rows:
        activity_id = str(row["activity_id"])
        fit_path = find_fit_file(root, activity_id)
        results.append(
            {
                "activity_id": activity_id,
                "name": row["name"],
                "start_time": row["start_time"],
                "elapsed_time": row["elapsed_time"],
                "distance": row["distance"],
                "distance_units": units,
                "avg_hr": row["avg_hr"],
                "max_hr": row["max_hr"],
                "sub_sport": row["sub_sport"],
                "self_evaluation": {
                    "feel": row["self_eval_feel"],
                    "effort": row["self_eval_effort"],
                },
                "detail_coverage": {
                    "summary_laps": row["summary_laps"],
                    "lap_rows": row["lap_rows"],
                    "record_rows": row["record_rows"],
                    "gps_record_rows": row["gps_record_rows"],
                    "split_rows": row["split_rows"],
                },
                "fit_file": relative_path(fit_path, root) if fit_path else None,
            }
        )
    return results


def print_text(runs: list[dict[str, object]]) -> None:
    if not runs:
        print("No running activities found in GarminDB.")
        return
    for run in runs:
        print(
            f"{run['activity_id']} | {run['start_time']} | {run['name']} | "
            f"{run['distance']} {run['distance_units']} | {run['elapsed_time']} | "
            f"saved feel/effort: {run['self_evaluation']} | "
            f"detail: {run['detail_coverage']} | FIT: {run['fit_file'] or 'not found'}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List recent GarminDB running activities and their FIT files."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--date", type=parse_iso_date)
    parser.add_argument("--start-date", type=parse_iso_date)
    parser.add_argument("--end-date", type=parse_iso_date)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        parser.error("--limit must be between 1 and 100")
    if args.date and (args.start_date or args.end_date):
        parser.error("--date cannot be combined with --start-date or --end-date")
    if bool(args.start_date) != bool(args.end_date):
        parser.error("--start-date and --end-date must be supplied together")
    if args.start_date and args.end_date and args.start_date > args.end_date:
        parser.error("--start-date cannot be after --end-date")

    root = args.project_root.expanduser().resolve()
    try:
        runs = list_runs(
            root,
            args.limit,
            exact_date=args.date,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    except (FileNotFoundError, sqlite3.Error) as error:
        parser.exit(2, f"ERROR: {error}\n")

    if args.json:
        print(json.dumps(runs, indent=2))
    else:
        print_text(runs)


if __name__ == "__main__":
    main()
