#!/usr/bin/env python3
"""Manage the private SQLite running record and compact Markdown projections."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable


DB_NAME = "running_data.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "running_data" / "migrations"
MILES_TO_METERS = 1609.344
CURRENT_PROFILE_SECTIONS = (
    "Athlete Baseline",
    "Goals and Event Context",
    "Estimates and Open Inputs",
    "Runner Profile",
    "Training Zones and Pacing",
    "Active Running Plan",
)
CURRENT_PLAN_SECTIONS = (
    "Plan Status",
    "This Week's Plan",
    "Planning Assumptions",
    "Training Intensity Rules",
    "Development Horizon and Conditional Event Build",
    "About a 20 Miler",
    "Wednesday Workout Menu",
    "Fueling Practice",
    "Shoe Plan",
    "Injury Watchlist",
    "Strength and Cross-Training",
    "Adjustment Rules",
    "Questions to Resolve",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require_project(root: Path) -> None:
    if not (root / "AGENTS.md").is_file():
        raise RuntimeError(f"AGENTS.md not found under project root: {root}")


def database_path(root: Path) -> Path:
    return root / "docs" / DB_NAME


def connect(root: Path, readonly: bool = False) -> sqlite3.Connection:
    path = database_path(root)
    if readonly:
        if not path.is_file():
            raise RuntimeError(f"Running database not found: {path}")
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only = ON")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def apply_migrations(connection: sqlite3.Connection) -> list[int]:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        )
        """
    )
    applied: list[int] = []
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(path.name.split("_", 1)[0])
        sql = path.read_text(encoding="utf-8")
        checksum = sha256_bytes(sql.encode("utf-8"))
        row = connection.execute(
            "SELECT checksum FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        if row:
            if row["checksum"] != checksum:
                raise RuntimeError(f"Applied migration checksum changed: {path.name}")
            continue
        connection.executescript(sql)
        connection.execute(
            "INSERT INTO schema_migrations(version, name, applied_at, checksum) VALUES (?, ?, ?, ?)",
            (version, path.name, utc_now(), checksum),
        )
        connection.commit()
        applied.append(version)
    return applied


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def parse_markdown_sections(text: str) -> tuple[str, dict[str, str]]:
    preface: list[str] = []
    sections: dict[str, str] = {}
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                sections[title] = "\n".join(body).strip()
            title = line[3:].strip()
            body = []
        elif title is None:
            preface.append(line)
        else:
            body.append(line)
    if title is not None:
        sections[title] = "\n".join(body).strip()
    return "\n".join(preface).strip(), sections


def markdown_updated_on(text: str) -> str:
    match = re.search(r"(?im)^Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else date.today().isoformat()


def parse_duration_seconds(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    match = re.search(r"(?<!\d)(\d{1,2}):(\d{2}):(\d{2})(?!\d)", text)
    if match:
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
    match = re.search(r"(?<!\d)(\d{1,3}):(\d{2})(?!\d)", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    hours = re.search(r"(\d+(?:\.\d+)?)\s*h(?:ours?|r)?\b", text, re.I)
    minutes = re.search(r"(\d+(?:\.\d+)?)\s*m(?:in(?:utes?)?)?\b", text, re.I)
    if hours or minutes:
        return round((float(hours.group(1)) if hours else 0) * 3600 + (float(minutes.group(1)) if minutes else 0) * 60)
    return None


def parse_distance_meters(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*mi(?:les?)?\b", str(value), re.I)
    return float(match.group(1)) * MILES_TO_METERS if match else None


def parse_pace_sec_per_km(value: Any) -> float | None:
    if value is None:
        return None
    match = re.search(r"(\d{1,2}):(\d{2})\s*/\s*mi", str(value), re.I)
    if not match:
        return None
    seconds_per_mile = int(match.group(1)) * 60 + int(match.group(2))
    return seconds_per_mile / 1.609344


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def source_type(source: str) -> str:
    lowered = source.lower()
    if "garmindb" in lowered and ("user" in lowered or "athlete" in lowered):
        return "mixed"
    if "garmindb" in lowered:
        return "garmindb"
    if "garmin" in lowered:
        return "garmin"
    return "manual"


def upsert_recovery_entry(connection: sqlite3.Connection, entry: dict[str, Any]) -> dict[str, int]:
    recovery_date = entry.get("date")
    if not isinstance(recovery_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", recovery_date):
        raise ValueError("Recovery entry requires date in YYYY-MM-DD form")
    sleep = entry.get("sleep_details") if isinstance(entry.get("sleep_details"), dict) else {}
    hrv = entry.get("hrv") if isinstance(entry.get("hrv"), dict) else {}
    readiness = entry.get("training_readiness") if isinstance(entry.get("training_readiness"), dict) else {}
    bb = entry.get("body_battery_stress") if isinstance(entry.get("body_battery_stress"), dict) else {}
    battery = bb.get("body_battery") if isinstance(bb.get("body_battery"), dict) else {}
    stress = bb.get("stress") if isinstance(bb.get("stress"), dict) else {}
    source = str(entry.get("source") or "unspecified")
    payload = canonical_json(entry)
    ref = f"recovery:{recovery_date}:{sha256_bytes(payload.encode())[:16]}"
    connection.execute(
        """
        INSERT INTO recovery_daily(
            recovery_date, sleep_start_at, sleep_end_at, sleep_duration_min,
            sleep_score, resting_hr_bpm, hrv_overnight_ms, hrv_status,
            training_readiness, body_battery_am, stress_avg, source_type,
            source_ref, notes, details_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(recovery_date) DO UPDATE SET
            sleep_start_at = excluded.sleep_start_at,
            sleep_end_at = excluded.sleep_end_at,
            sleep_duration_min = excluded.sleep_duration_min,
            sleep_score = excluded.sleep_score,
            resting_hr_bpm = excluded.resting_hr_bpm,
            hrv_overnight_ms = excluded.hrv_overnight_ms,
            hrv_status = excluded.hrv_status,
            training_readiness = excluded.training_readiness,
            body_battery_am = excluded.body_battery_am,
            stress_avg = excluded.stress_avg,
            source_type = excluded.source_type,
            source_ref = excluded.source_ref,
            notes = excluded.notes,
            details_json = excluded.details_json,
            updated_at = excluded.updated_at
        """,
        (
            recovery_date,
            sleep.get("bed_time") or sleep.get("garmin_main_sleep_start"),
            sleep.get("wake_time") or sleep.get("garmin_main_sleep_end"),
            entry.get("sleep_duration_minutes"),
            entry.get("sleep_score"),
            entry.get("resting_hr_bpm"),
            hrv.get("value_ms"),
            hrv.get("status"),
            readiness.get("score"),
            battery.get("daily_high") or battery.get("sleep_csv"),
            stress.get("avg"),
            source_type(source),
            ref,
            entry.get("notes"),
            payload,
            utc_now(),
        ),
    )
    observation_count = 0
    for kind, key in (("soreness_or_pain", "soreness_or_pain"), ("illness_or_fatigue", "illness_or_fatigue")):
        note = entry.get(key)
        if not isinstance(note, str) or not note.strip():
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO recovery_observations(
                recovery_date, observed_at, kind, note
            ) VALUES (?, ?, ?, ?)
            """,
            (recovery_date, recovery_date, kind, note.strip()),
        )
        observation_count += connection.execute("SELECT changes()").fetchone()[0]
    activity_count = 0
    run = entry.get("run_response")
    if isinstance(run, dict):
        activity_count = upsert_activity_from_mapping(connection, recovery_date, run)
    return {"recovery_daily": 1, "recovery_observations": observation_count, "activity_reviews": activity_count}


def upsert_activity_from_mapping(connection: sqlite3.Connection, fallback_date: str, run: dict[str, Any]) -> int:
    if run.get("source_activity_id") is not None:
        source_id = str(run["source_activity_id"])
    elif run.get("activity_id") is not None:
        source_id = f"garmin:{run['activity_id']}"
    elif run.get("activity_file") is not None:
        source_id = f"file:{run['activity_file']}"
    else:
        source_id = f"activity:{sha256_bytes(canonical_json(run).encode())[:16]}"
    distance_m = float(run["distance_m"]) if run.get("distance_m") is not None else None
    if distance_m is None:
        distance_mi = run.get("distance_miles")
        if distance_mi is None:
            distance_mi = run.get("distance_mi")
        distance_m = float(distance_mi) * MILES_TO_METERS if distance_mi is not None else parse_distance_meters(run.get("notes"))
    duration = int(run["duration_s"]) if run.get("duration_s") is not None else None
    if duration is None:
        for key in ("timer_time", "moving_duration", "duration", "elapsed_duration", "elapsed_time"):
            duration = parse_duration_seconds(run.get(key))
            if duration is not None:
                break
    avg_hr = run.get("avg_hr_bpm") if run.get("avg_hr_bpm") is not None else run.get("average_hr_bpm")
    pace = float(run["avg_pace_sec_per_km"]) if run.get("avg_pace_sec_per_km") is not None else None
    if pace is None:
        for key in ("timer_pace", "moving_pace", "pace", "elapsed_pace"):
            pace = parse_pace_sec_per_km(run.get(key))
            if pace is not None:
                break
    effort = str(run.get("athlete_reported_effort") or "")
    rpe_match = re.search(r"\b(10|[1-9])\s*/\s*10\b", effort)
    rpe = int(run["rpe"]) if run.get("rpe") is not None else (int(rpe_match.group(1)) if rpe_match else None)
    outcome = run.get("outcome") or run.get("interpretation") or run.get("subjective_response") or run.get("notes")
    started_at = str(run.get("start_local") or fallback_date)
    connection.execute(
        """
        INSERT INTO activity_reviews(
            source_activity_id, started_at, distance_m, duration_s, avg_hr_bpm,
            avg_pace_sec_per_km, rpe, outcome, details_json, reviewed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_activity_id) DO UPDATE SET
            started_at = excluded.started_at,
            distance_m = excluded.distance_m,
            duration_s = excluded.duration_s,
            avg_hr_bpm = excluded.avg_hr_bpm,
            avg_pace_sec_per_km = excluded.avg_pace_sec_per_km,
            rpe = excluded.rpe,
            outcome = excluded.outcome,
            details_json = excluded.details_json,
            reviewed_at = excluded.reviewed_at
        """,
        (
            source_id,
            started_at,
            distance_m,
            duration,
            round(float(avg_hr)) if avg_hr is not None else None,
            pace,
            rpe,
            outcome,
            canonical_json(run),
            utc_now(),
        ),
    )
    return 1


def upsert_profile_sections(connection: sqlite3.Connection, text: str) -> int:
    _, sections = parse_markdown_sections(text)
    valid_from = markdown_updated_on(text)
    count = 0
    for title, body in sections.items():
        current = title in CURRENT_PROFILE_SECTIONS
        category = "current_profile_section" if current else "legacy_profile_history"
        key = f"profile-section:{slugify(title)}"
        connection.execute(
            """
            INSERT INTO profile_entries(
                category, entry_key, value_text, valid_from, valid_to,
                source_type, source_ref, recorded_at
            ) VALUES (?, ?, ?, ?, ?, 'legacy_markdown', ?, ?)
            ON CONFLICT(entry_key, valid_from) DO UPDATE SET
                category = excluded.category,
                value_text = excluded.value_text,
                valid_to = excluded.valid_to,
                source_type = excluded.source_type,
                source_ref = excluded.source_ref,
                recorded_at = excluded.recorded_at
            """,
            (
                category,
                key,
                body,
                valid_from,
                None if current else valid_from,
                f"runner_profile.md#{slugify(title)}",
                utc_now(),
            ),
        )
        count += 1
    import_profile_measurements(connection, text, valid_from)
    import_profile_summaries(connection, sections.get("Facts Supported by Running Data", ""))
    import_profile_activities(connection, sections.get("Facts Supported by Running Data", ""))
    return count


def import_profile_measurements(connection: sqlite3.Connection, text: str, measured_on: str) -> None:
    patterns = {
        "age_years": r"(?im)^- Age:\s*(\d+(?:\.\d+)?)",
        "height_in": r"(?im)^- Height:\s*(\d+)\s*ft\s*(\d+)\s*in",
        "weight_lb": r"(?im)^- Weight used for planning:\s*(?:about\s*)?(\d+(?:\.\d+)?)\s*lb",
        "resting_hr_bpm": r"(?im)^- Garmin resting HR estimate:\s*(\d+(?:\.\d+)?)\s*bpm",
        "max_hr_bpm": r"(?im)^- Garmin max HR estimate:\s*(\d+(?:\.\d+)?)\s*bpm",
        "vo2max_ml_kg_min": r"(?im)^- Garmin VO2 max estimate:\s*(\d+(?:\.\d+)?)",
        "lactate_threshold_hr_bpm": r"(?im)^- Garmin running lactate-threshold estimate.*?:\s*(\d+)\s*bpm",
    }
    for metric, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            continue
        value = float(match.group(1))
        if metric == "height_in":
            value = float(match.group(1)) * 12 + float(match.group(2))
        connection.execute(
            """
            INSERT INTO profile_measurements(
                measured_on, metric_key, value_num, source_type, source_ref, recorded_at
            ) VALUES (?, ?, ?, 'legacy_markdown', ?, ?)
            ON CONFLICT(measured_on, metric_key, source_type) DO UPDATE SET
                value_num = excluded.value_num,
                source_ref = excluded.source_ref,
                recorded_at = excluded.recorded_at
            """,
            (measured_on, metric, value, "runner_profile.md#athlete-baseline", utc_now()),
        )
    threshold = re.search(
        r"(?im)^- Garmin running lactate-threshold estimate.*?:\s*\d+\s*bpm,\s*(\d+):(\d+)/mi,\s*(\d+(?:\.\d+)?)\s*W,\s*(\d+(?:\.\d+)?)\s*W/kg",
        text,
    )
    if threshold:
        values = {
            "lactate_threshold_pace_sec_per_mile": int(threshold.group(1)) * 60 + int(threshold.group(2)),
            "lactate_threshold_power_w": float(threshold.group(3)),
            "lactate_threshold_power_w_per_kg": float(threshold.group(4)),
        }
        for metric, value in values.items():
            connection.execute(
                """
                INSERT INTO profile_measurements(
                    measured_on, metric_key, value_num, source_type, source_ref, recorded_at
                ) VALUES (?, ?, ?, 'legacy_markdown', ?, ?)
                ON CONFLICT(measured_on, metric_key, source_type) DO UPDATE SET
                    value_num = excluded.value_num,
                    source_ref = excluded.source_ref,
                    recorded_at = excluded.recorded_at
                """,
                (measured_on, metric, value, "runner_profile.md#athlete-baseline", utc_now()),
            )


def markdown_tables(text: str) -> Iterable[tuple[list[str], list[list[str]]]]:
    lines = text.splitlines()
    index = 0
    while index + 1 < len(lines):
        if lines[index].lstrip().startswith("|") and re.match(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", lines[index + 1]):
            header = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            yield header, rows
        else:
            index += 1


def number_from(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def import_profile_summaries(connection: sqlite3.Connection, body: str) -> None:
    for header, rows in markdown_tables(body):
        if not header:
            continue
        if header[0] == "Month":
            for row in rows:
                if len(row) < 3 or not re.fullmatch(r"\d{4}-\d{2}(?:.*)?", row[0]):
                    continue
                month_match = re.match(r"(\d{4})-(\d{2})", row[0])
                year, month = int(month_match.group(1)), int(month_match.group(2))
                start = date(year, month, 1)
                end = date(year, month, calendar.monthrange(year, month)[1])
                upsert_summary(connection, "month", start.isoformat(), end.isoformat(), row)
        elif header[0] == "Week Starting":
            for row in rows:
                if len(row) < 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0]):
                    continue
                start = date.fromisoformat(row[0])
                upsert_summary(connection, "week", start.isoformat(), (start + timedelta(days=6)).isoformat(), row)


def upsert_summary(connection: sqlite3.Connection, period_type: str, starts_on: str, ends_on: str, row: list[str]) -> None:
    run_count = number_from(row[1]) if len(row) > 1 else None
    distance_miles = number_from(row[2]) if len(row) > 2 else None
    connection.execute(
        """
        INSERT INTO training_summaries(
            period_type, starts_on, ends_on, run_count, distance_m,
            key_takeaway, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(period_type, starts_on, ends_on) DO UPDATE SET
            run_count = excluded.run_count,
            distance_m = excluded.distance_m,
            key_takeaway = excluded.key_takeaway,
            details_json = excluded.details_json
        """,
        (
            period_type,
            starts_on,
            ends_on,
            round(run_count) if run_count is not None else None,
            distance_miles * MILES_TO_METERS if distance_miles is not None else None,
            "Imported from the legacy runner-profile training ledger.",
            canonical_json({"legacy_row": row}),
        ),
    )


def import_profile_activities(connection: sqlite3.Connection, body: str) -> None:
    for match in re.finditer(r"(?m)^- (\d{4}-\d{2}-\d{2}):\s*(.+)$", body):
        activity_date, narrative = match.groups()
        distance_m = parse_distance_meters(narrative)
        existing = connection.execute(
            "SELECT * FROM activity_reviews WHERE substr(started_at, 1, 10) = ? ORDER BY activity_review_id",
            (activity_date,),
        ).fetchall()
        candidate = None
        for row in existing:
            if distance_m is None or row["distance_m"] is None or abs(row["distance_m"] - distance_m) < 250:
                candidate = row
                break
        if candidate:
            outcome = candidate["outcome"] or ""
            if narrative not in outcome:
                outcome = f"{outcome}\n\nLegacy profile evidence: {narrative}".strip()
                connection.execute(
                    "UPDATE activity_reviews SET outcome = ?, reviewed_at = ? WHERE activity_review_id = ?",
                    (outcome, utc_now(), candidate["activity_review_id"]),
                )
            continue
        duration = parse_duration_seconds(narrative)
        hr_match = re.search(r"(?:average|avg) HR(?: of| was)?\s*(?:about\s*)?(\d+(?:\.\d+)?)", narrative, re.I)
        source_id = f"legacy-profile:{activity_date}:{sha256_bytes(narrative.encode())[:12]}"
        connection.execute(
            """
            INSERT OR IGNORE INTO activity_reviews(
                source_activity_id, started_at, distance_m, duration_s, avg_hr_bpm,
                avg_pace_sec_per_km, outcome, details_json, reviewed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                activity_date,
                distance_m,
                duration,
                round(float(hr_match.group(1))) if hr_match else None,
                parse_pace_sec_per_km(narrative),
                narrative,
                canonical_json({"legacy_profile_narrative": narrative}),
                utc_now(),
            ),
        )


def bullet_value(body: str, label: str) -> str | None:
    match = re.search(rf"(?im)^- {re.escape(label)}:\s*(.+)$", body)
    return match.group(1).strip() if match else None


def import_event(connection: sqlite3.Connection, plan_status: str, profile_goals: str) -> int | None:
    line = bullet_value(plan_status, "Active event context") or bullet_value(profile_goals, "Active event context")
    if not line:
        return None
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", line)
    if not date_match:
        return None
    event_date = date_match.group()
    name_match = re.search(r"(?:use\s+)?(.+?)\s+on\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*\d{4}-\d{2}-\d{2}", line, re.I)
    name = name_match.group(1).strip(" ,.") if name_match else f"Event {event_date}"
    event_type = "marathon" if "marathon" in line.lower() else "running_event"
    distance_m = 42195 if event_type == "marathon" else None
    status = "tentative" if any(word in line.lower() for word in ("tentative", "not registered", "not confirmed")) else "confirmed"
    priority = "completion" if "completion" in plan_status.lower() else None
    connection.execute(
        """
        INSERT INTO events(name, event_date, event_type, distance_m, priority, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, event_date) DO UPDATE SET
            event_type = excluded.event_type,
            distance_m = excluded.distance_m,
            priority = excluded.priority,
            status = excluded.status,
            notes = excluded.notes
        """,
        (name, event_date, event_type, distance_m, priority, status, line),
    )
    return connection.execute(
        "SELECT event_id FROM events WHERE name = ? AND event_date = ?", (name, event_date)
    ).fetchone()[0]


def import_plan(connection: sqlite3.Connection, text: str, profile_text: str) -> dict[str, int]:
    _, sections = parse_markdown_sections(text)
    _, profile_sections = parse_markdown_sections(profile_text)
    updated_on = markdown_updated_on(text)
    status_body = sections.get("Plan Status", "")
    event_id = import_event(connection, status_body, profile_sections.get("Goals and Event Context", ""))
    block_line = bullet_value(status_body, "Current development block") or "Imported active training block"
    block_match = re.match(r"(.+?)(?:,|\s+from)\s+(\d{4}-\d{2}-\d{2})\s+(?:through|to)\s+(\d{4}-\d{2}-\d{2})", block_line)
    if block_match:
        block_name, starts_on, ends_on = block_match.groups()
    else:
        block_name = "Imported Active Plan"
        starts_on = updated_on
        ends_on = updated_on
    objective = bullet_value(status_body, "Primary development objective") or block_line
    reassess_text = bullet_value(status_body, "Development review points") or ""
    reassess_match = re.search(r"\d{4}-\d{2}-\d{2}", reassess_text)
    reassess_on = reassess_match.group() if reassess_match else ends_on
    connection.execute("UPDATE training_blocks SET status = 'historical' WHERE status = 'active' AND name <> ?", (block_name,))
    connection.execute(
        """
        INSERT INTO training_blocks(
            event_id, name, objective, starts_on, ends_on, status, reassess_on, notes
        ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
        ON CONFLICT(name, starts_on) DO UPDATE SET
            event_id = excluded.event_id,
            objective = excluded.objective,
            ends_on = excluded.ends_on,
            status = excluded.status,
            reassess_on = excluded.reassess_on,
            notes = excluded.notes
        """,
        (event_id, block_name.strip(), objective, starts_on, ends_on, reassess_on, block_line),
    )
    block_id = connection.execute(
        "SELECT block_id FROM training_blocks WHERE name = ? AND starts_on = ?", (block_name.strip(), starts_on)
    ).fetchone()[0]
    week_count = session_count = item_count = 0
    for section_name, week_status in (("Previous Week", "completed"), ("This Week's Plan", "active")):
        body = sections.get(section_name)
        if not body:
            continue
        week_match = re.search(r"(?im)^Week:\s*(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", body)
        if not week_match:
            continue
        week_start, week_end = week_match.groups()
        objective_match = re.search(r"(?im)^(?:Operating goal|The athlete requested[^:]*|\- Target):\s*(.+)$", body)
        week_objective = objective_match.group(1).strip() if objective_match else section_name
        target_match = re.search(r"(?im)^- (?:Revised weekly target|Target):\s*(?:about\s*)?(\d+(?:\.\d+)?)\s*mi", body)
        target_m = float(target_match.group(1)) * MILES_TO_METERS if target_match else None
        connection.execute(
            """
            INSERT INTO plan_weeks(block_id, starts_on, ends_on, objective, target_distance_m, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(block_id, starts_on) DO UPDATE SET
                ends_on = excluded.ends_on,
                objective = excluded.objective,
                target_distance_m = excluded.target_distance_m,
                status = excluded.status
            """,
            (block_id, week_start, week_end, week_objective, target_m, week_status),
        )
        week_id = connection.execute(
            "SELECT week_id FROM plan_weeks WHERE block_id = ? AND starts_on = ?", (block_id, week_start)
        ).fetchone()[0]
        week_count += 1
        for header, rows in markdown_tables(body):
            if not header or header[0] != "Day":
                continue
            for row in rows:
                if len(row) < 5:
                    continue
                date_match = re.search(r"\d{4}-\d{2}-\d{2}", row[0])
                if not date_match:
                    continue
                planned_date = date_match.group()
                title = row[1]
                lowered = title.lower()
                if "rest" in lowered or "unavailable" in lowered:
                    session_type = "rest"
                elif "long" in lowered or "distance" in lowered:
                    session_type = "long_run"
                elif any(word in lowered for word in ("tempo", "interval", "quality", "hill", "stride")):
                    session_type = "quality"
                elif "easy" in lowered or "run" in lowered:
                    session_type = "easy_run"
                else:
                    session_type = "other"
                session_status = "completed" if "completed" in lowered or (planned_date < updated_on and week_status == "completed") else "planned"
                if session_type == "rest" and planned_date <= updated_on:
                    session_status = "completed"
                distance_m = parse_distance_meters(row[2])
                duration_s = parse_duration_seconds(row[2]) if distance_m is None else None
                connection.execute(
                    """
                    INSERT INTO plan_sessions(
                        week_id, planned_date, session_type, title, status,
                        target_distance_m, target_duration_s, intensity, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(week_id, planned_date, title) DO UPDATE SET
                        session_type = excluded.session_type,
                        status = excluded.status,
                        target_distance_m = excluded.target_distance_m,
                        target_duration_s = excluded.target_duration_s,
                        intensity = excluded.intensity,
                        notes = excluded.notes
                    """,
                    (week_id, planned_date, session_type, title, session_status, distance_m, duration_s, row[3], row[4]),
                )
                session_id = connection.execute(
                    "SELECT session_id FROM plan_sessions WHERE week_id = ? AND planned_date = ? AND title = ?",
                    (week_id, planned_date, title),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO plan_items(
                        session_id, sequence_no, item_type, target_distance_m,
                        target_duration_s, intensity, instructions
                    ) VALUES (?, 1, 'session_instructions', ?, ?, ?, ?)
                    ON CONFLICT(session_id, sequence_no) DO UPDATE SET
                        target_distance_m = excluded.target_distance_m,
                        target_duration_s = excluded.target_duration_s,
                        intensity = excluded.intensity,
                        instructions = excluded.instructions
                    """,
                    (session_id, distance_m, duration_s, row[3], row[4]),
                )
                connection.execute(
                    """
                    UPDATE activity_reviews
                    SET plan_session_id = ?
                    WHERE activity_review_id = (
                        SELECT activity_review_id FROM activity_reviews
                        WHERE substr(started_at, 1, 10) = ? AND plan_session_id IS NULL
                        ORDER BY activity_review_id LIMIT 1
                    )
                    """,
                    (session_id, planned_date),
                )
                session_count += 1
                item_count += 1
    adjustment_count = 0
    for title, body in sections.items():
        source_ref = f"running_plan.md#{slugify(title)}"
        connection.execute(
            """
            INSERT INTO plan_adjustments(
                block_id, adjusted_at, reason, decision, source_type, source_ref
            ) VALUES (?, ?, ?, ?, 'legacy_markdown', ?)
            ON CONFLICT(source_type, source_ref) WHERE source_ref IS NOT NULL DO UPDATE SET
                block_id = excluded.block_id,
                adjusted_at = excluded.adjusted_at,
                reason = excluded.reason,
                decision = excluded.decision
            """,
            (block_id, f"{updated_on}T00:00:00", title, body, source_ref),
        )
        adjustment_count += 1
    return {
        "training_blocks": 1,
        "plan_weeks": week_count,
        "plan_sessions": session_count,
        "plan_items": item_count,
        "plan_adjustments": adjustment_count,
        "events": 1 if event_id else 0,
    }


def import_legacy(root: Path, connection: sqlite3.Connection) -> dict[str, int]:
    docs = root / "docs"
    raw_path = docs / "recovery_metrics_raw.json"
    profile_path = docs / "runner_profile.md"
    plan_path = docs / "running_plan.md"
    missing = [str(path) for path in (raw_path, profile_path, plan_path) if not path.is_file()]
    if missing:
        raise RuntimeError(f"Legacy source files missing: {', '.join(missing)}")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    entries = raw.get("entries") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        raise RuntimeError("Legacy recovery JSON does not contain an entries list")
    report: dict[str, int] = {"source_recovery_entries": len(entries)}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Every legacy recovery entry must be an object")
        for key, count in upsert_recovery_entry(connection, entry).items():
            report[key] = report.get(key, 0) + count
    profile_text = profile_path.read_text(encoding="utf-8")
    plan_text = plan_path.read_text(encoding="utf-8")
    report["profile_entries"] = upsert_profile_sections(connection, profile_text)
    for key, count in import_plan(connection, plan_text, profile_text).items():
        report[key] = count
    connection.commit()
    return report


def verify_database(connection: sqlite3.Connection, expected_recovery: int | None = None) -> dict[str, Any]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = [dict(row) for row in connection.execute("PRAGMA foreign_key_check")]
    tables = [
        "schema_migrations", "recovery_daily", "recovery_observations", "profile_entries",
        "profile_measurements", "events", "training_summaries", "activity_reviews",
        "training_blocks", "plan_weeks", "plan_sessions", "plan_items", "plan_adjustments",
    ]
    counts = {table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables}
    duplicate_recovery = connection.execute(
        "SELECT count(*) - count(DISTINCT recovery_date) FROM recovery_daily"
    ).fetchone()[0]
    result = {
        "integrity_check": integrity,
        "foreign_key_violations": foreign_keys,
        "counts": counts,
        "duplicate_recovery_dates": duplicate_recovery,
        "expected_recovery_entries": expected_recovery,
    }
    if integrity != "ok" or foreign_keys or duplicate_recovery:
        raise RuntimeError(f"Database verification failed: {json.dumps(result, default=str)}")
    if expected_recovery is not None and counts["recovery_daily"] != expected_recovery:
        raise RuntimeError(
            f"Recovery reconciliation failed: expected {expected_recovery}, found {counts['recovery_daily']}"
        )
    return result


def compact(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_recovery(root: Path, connection: sqlite3.Connection, limit: int = 14) -> None:
    rows = connection.execute(
        "SELECT * FROM v_recovery_recent ORDER BY recovery_date DESC LIMIT ?", (limit,)
    ).fetchall()
    latest = rows[0]["recovery_date"] if rows else "not available"
    lines = [
        "# Recovery Metrics",
        "",
        f"Last updated: {latest}",
        "",
        "Historical source of truth: `docs/running_data.db`. Query the database for older entries or full source detail.",
        "",
        "## Use Rules",
        "",
        "- This file is a compact projection of the most recent 14 recovery days.",
        "- Use the most recent 7 valid entries for immediate training decisions unless a longer review is requested.",
        "- Interpret clusters across sleep, HRV, resting HR, symptoms, recent load, and run response; do not react to one metric alone.",
        "",
        "## Rolling Daily Log",
        "",
        "| Date | Sleep | Score | RHR | HRV | Readiness | Body Battery / Stress | Observations | Training implication |",
        "|---|---:|---:|---:|---|---:|---|---|---|",
    ]
    for row in rows:
        details = json.loads(row["details_json"])
        sleep = details.get("sleep_duration") or (f"{row['sleep_duration_min']} min" if row["sleep_duration_min"] is not None else "--")
        hrv_extra = nested(details, "hrv", "seven_day_average_ms")
        hrv = "--" if row["hrv_overnight_ms"] is None else f"{row['hrv_overnight_ms']:g} ms"
        if hrv_extra is not None:
            hrv += f"; 7d {hrv_extra}"
        if row["hrv_status"]:
            hrv += f" {row['hrv_status']}"
        battery = "--"
        if row["body_battery_am"] is not None or row["stress_avg"] is not None:
            battery = f"BB {row['body_battery_am'] if row['body_battery_am'] is not None else '--'}; stress {row['stress_avg'] if row['stress_avg'] is not None else '--'}"
        lines.append(
            "| " + " | ".join(
                [
                    row["recovery_date"], compact(sleep, 80), str(row["sleep_score"] or "--"),
                    str(row["resting_hr_bpm"] or "--"), compact(hrv, 90),
                    str(row["training_readiness"] or "--"), compact(battery, 90),
                    compact(row["observations"], 180) or "--", compact(row["notes"], 260) or "--",
                ]
            ) + " |"
        )
    (root / "docs" / "recovery_metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_profile(root: Path, connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT * FROM v_current_profile WHERE category = 'current_profile_section'"
    ).fetchall()
    by_key = {row["entry_key"].split(":", 1)[-1]: row for row in rows}
    updated = max((row["valid_from"] for row in rows), default=date.today().isoformat())
    lines = [
        "# Runner Profile", "", f"Last updated: {updated}", "",
        "Historical activity evidence, prior assessments, and processed-source detail are stored in `docs/running_data.db`.",
        "Query the database when older evidence is needed; keep this file limited to current coaching context.", "",
    ]
    for title in CURRENT_PROFILE_SECTIONS:
        row = by_key.get(slugify(title))
        if row and row["value_text"].strip():
            lines.extend([f"## {title}", "", row["value_text"].strip(), ""])
    (root / "docs" / "runner_profile.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_plan(root: Path, connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT p.* FROM plan_adjustments AS p
        JOIN (
            SELECT reason, max(adjustment_id) AS adjustment_id
            FROM plan_adjustments GROUP BY reason
        ) AS latest ON latest.adjustment_id = p.adjustment_id
        """
    ).fetchall()
    by_reason = {row["reason"]: row for row in rows}
    updated = max((str(row["adjusted_at"])[:10] for row in rows), default=date.today().isoformat())
    lines = [
        "# Running Plan", "", f"Last updated: {updated}", "",
        "Historical weeks, completed sessions, and prior adjustments are stored in `docs/running_data.db`.",
        "Query the database for plan history; keep this file focused on the active operating plan.", "",
    ]
    for title in CURRENT_PLAN_SECTIONS:
        row = by_reason.get(title)
        if row and row["decision"].strip():
            lines.extend([f"## {title}", "", row["decision"].strip(), ""])
    (root / "docs" / "running_plan.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def render_all(root: Path, connection: sqlite3.Connection) -> None:
    render_recovery(root, connection)
    render_profile(root, connection)
    render_plan(root, connection)
    for name in ("recovery_metrics.md", "runner_profile.md", "running_plan.md"):
        try:
            os.chmod(root / "docs" / name, 0o600)
        except OSError:
            pass


def archive_sources(root: Path) -> tuple[Path, dict[str, Any]]:
    docs = root / "docs"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = docs / "archive" / f"sqlite-cutover-{stamp}"
    archive.mkdir(parents=True, mode=0o700, exist_ok=False)
    try:
        os.chmod(archive, 0o700)
    except OSError:
        pass
    manifest: dict[str, Any] = {"created_at": utc_now(), "files": {}}
    names = ("recovery_metrics_raw.json", "recovery_metrics.md", "runner_profile.md", "running_plan.md")
    for name in names:
        source = docs / name
        if not source.is_file():
            raise RuntimeError(f"Cannot archive missing source: {source}")
        destination = archive / name
        shutil.copy2(source, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
        source_hash = sha256_file(source)
        if sha256_file(destination) != source_hash:
            raise RuntimeError(f"Archive checksum mismatch for {name}")
        manifest["files"][name] = {"sha256": source_hash, "bytes": source.stat().st_size}
    manifest_path = archive / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(manifest_path, 0o600)
    except OSError:
        pass
    raw = docs / "recovery_metrics_raw.json"
    raw.unlink()
    return archive, manifest


def context_payload(connection: sqlite3.Connection, section: str, days: int) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if section in ("all", "recovery"):
        payload["recovery"] = [dict(row) for row in connection.execute(
            "SELECT * FROM v_recovery_recent ORDER BY recovery_date DESC LIMIT ?", (days,)
        )]
    if section in ("all", "profile"):
        payload["profile_entries"] = [dict(row) for row in connection.execute(
            "SELECT * FROM v_current_profile ORDER BY category, entry_key"
        )]
        payload["latest_measurements"] = [dict(row) for row in connection.execute(
            """
            SELECT p.* FROM profile_measurements AS p
            JOIN (SELECT metric_key, max(measured_on) measured_on FROM profile_measurements GROUP BY metric_key) AS m
              ON m.metric_key = p.metric_key AND m.measured_on = p.measured_on
            ORDER BY p.metric_key
            """
        )]
        payload["events"] = [dict(row) for row in connection.execute(
            "SELECT * FROM events WHERE status <> 'completed' ORDER BY event_date"
        )]
    if section in ("all", "plan"):
        payload["plan"] = [dict(row) for row in connection.execute(
            "SELECT * FROM v_current_plan ORDER BY week_starts_on, planned_date"
        )]
        payload["recent_adjustments"] = [dict(row) for row in connection.execute(
            "SELECT * FROM plan_adjustments ORDER BY adjusted_at DESC, adjustment_id DESC LIMIT ?", (days,)
        )]
    return payload


def history_payload(connection: sqlite3.Connection, kind: str, start: str | None, end: str | None, limit: int) -> list[dict[str, Any]]:
    mapping = {
        "recovery": ("v_recovery_recent", "recovery_date"),
        "activities": ("activity_reviews", "substr(started_at, 1, 10)"),
        "summaries": ("training_summaries", "starts_on"),
        "adjustments": ("plan_adjustments", "substr(adjusted_at, 1, 10)"),
        "profile": ("profile_entries", "valid_from"),
    }
    table, column = mapping[kind]
    clauses: list[str] = []
    params: list[Any] = []
    if start:
        clauses.append(f"{column} >= ?")
        params.append(start)
    if end:
        clauses.append(f"{column} <= ?")
        params.append(end)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    return [dict(row) for row in connection.execute(
        f"SELECT * FROM {table}{where} ORDER BY {column} DESC LIMIT ?", params
    )]


def load_json_input(path: str) -> dict[str, Any]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Input JSON must be an object")
    return value


def set_profile_section(connection: sqlite3.Connection, section: str, value: str, effective_on: str, source_ref: str | None) -> None:
    key = f"profile-section:{slugify(section)}"
    same_version = connection.execute(
        "SELECT profile_entry_id FROM profile_entries WHERE entry_key = ? AND valid_from = ?",
        (key, effective_on),
    ).fetchone()
    connection.execute(
        "UPDATE profile_entries SET valid_to = ? WHERE entry_key = ? AND valid_to IS NULL AND valid_from <> ?",
        (effective_on, key, effective_on),
    )
    if same_version:
        connection.execute(
            """
            UPDATE profile_entries
            SET category = 'current_profile_section', value_text = ?, valid_to = NULL,
                source_type = 'agent', source_ref = ?, recorded_at = ?
            WHERE profile_entry_id = ?
            """,
            (value, source_ref, utc_now(), same_version["profile_entry_id"]),
        )
    else:
        connection.execute(
            """
            INSERT INTO profile_entries(
                category, entry_key, value_text, valid_from, source_type, source_ref, recorded_at
            ) VALUES ('current_profile_section', ?, ?, ?, 'agent', ?, ?)
            """,
            (key, value, effective_on, source_ref, utc_now()),
        )


def record_profile_measurement(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO profile_measurements(
            measured_on, metric_key, value_num, source_type, source_ref, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(measured_on, metric_key, source_type) DO UPDATE SET
            value_num = excluded.value_num,
            source_ref = excluded.source_ref,
            recorded_at = excluded.recorded_at
        """,
        (
            payload["measured_on"], payload["metric_key"], float(payload["value_num"]),
            payload.get("source_type") or "agent", payload.get("source_ref"), utc_now(),
        ),
    )


def upsert_event_payload(connection: sqlite3.Connection, payload: dict[str, Any]) -> int:
    connection.execute(
        """
        INSERT INTO events(name, event_date, event_type, distance_m, priority, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, event_date) DO UPDATE SET
            event_type = excluded.event_type,
            distance_m = excluded.distance_m,
            priority = excluded.priority,
            status = excluded.status,
            notes = excluded.notes
        """,
        (
            payload["name"], payload["event_date"], payload.get("event_type") or "running_event",
            payload.get("distance_m"), payload.get("priority"), payload.get("status") or "tentative",
            payload.get("notes"),
        ),
    )
    return connection.execute(
        "SELECT event_id FROM events WHERE name = ? AND event_date = ?",
        (payload["name"], payload["event_date"]),
    ).fetchone()[0]


def record_summary_payload(connection: sqlite3.Connection, payload: dict[str, Any]) -> int:
    connection.execute(
        """
        INSERT INTO training_summaries(
            period_type, starts_on, ends_on, run_count, distance_m, duration_s,
            load_value, key_takeaway, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(period_type, starts_on, ends_on) DO UPDATE SET
            run_count = excluded.run_count,
            distance_m = excluded.distance_m,
            duration_s = excluded.duration_s,
            load_value = excluded.load_value,
            key_takeaway = excluded.key_takeaway,
            details_json = excluded.details_json
        """,
        (
            payload["period_type"], payload["starts_on"], payload["ends_on"], payload.get("run_count"),
            payload.get("distance_m"), payload.get("duration_s"), payload.get("load_value"),
            payload.get("key_takeaway"), canonical_json(payload.get("details") or {}),
        ),
    )
    return connection.execute(
        "SELECT summary_id FROM training_summaries WHERE period_type = ? AND starts_on = ? AND ends_on = ?",
        (payload["period_type"], payload["starts_on"], payload["ends_on"]),
    ).fetchone()[0]


def record_plan_adjustment(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    target_type = payload.get("target_type")
    target_id = payload.get("target_id")
    if target_type is None and target_id is None:
        row = connection.execute(
            "SELECT block_id FROM training_blocks WHERE status = 'active' ORDER BY starts_on DESC LIMIT 1"
        ).fetchone()
        if not row:
            raise ValueError("No active training block exists for the plan adjustment")
        target_type, target_id = "block", row["block_id"]
    if target_type not in {"block", "week", "session", "item"} or not isinstance(target_id, int):
        raise ValueError("Plan adjustment requires target_type and integer target_id, or an active block")
    columns = {"block": "block_id", "week": "week_id", "session": "session_id", "item": "item_id"}
    values = {name: None for name in columns.values()}
    values[columns[target_type]] = target_id
    connection.execute(
        """
        INSERT INTO plan_adjustments(
            block_id, week_id, session_id, item_id, adjusted_at,
            reason, decision, source_type, source_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_type, source_ref) WHERE source_ref IS NOT NULL DO UPDATE SET
            block_id = excluded.block_id,
            week_id = excluded.week_id,
            session_id = excluded.session_id,
            item_id = excluded.item_id,
            adjusted_at = excluded.adjusted_at,
            reason = excluded.reason,
            decision = excluded.decision
        """,
        (
            values["block_id"], values["week_id"], values["session_id"], values["item_id"],
            payload.get("adjusted_at") or utc_now(), payload["reason"], payload["decision"],
            payload.get("source_type") or "agent", payload.get("source_ref"),
        ),
    )


def upsert_plan_payload(connection: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, int]:
    block = payload.get("block")
    if not isinstance(block, dict):
        raise ValueError("Plan input requires a block object")
    required = ("name", "objective", "starts_on", "ends_on")
    missing = [key for key in required if not block.get(key)]
    if missing:
        raise ValueError(f"Plan block missing required fields: {', '.join(missing)}")
    status = block.get("status") or "active"
    if payload.get("replace_active", True) and status == "active":
        connection.execute(
            "UPDATE training_blocks SET status = 'historical' WHERE status = 'active' AND name <> ?",
            (block["name"],),
        )
    connection.execute(
        """
        INSERT INTO training_blocks(
            event_id, name, objective, starts_on, ends_on, status, reassess_on, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name, starts_on) DO UPDATE SET
            event_id = excluded.event_id,
            objective = excluded.objective,
            ends_on = excluded.ends_on,
            status = excluded.status,
            reassess_on = excluded.reassess_on,
            notes = excluded.notes
        """,
        (
            block.get("event_id"), block["name"], block["objective"], block["starts_on"],
            block["ends_on"], status, block.get("reassess_on"), block.get("notes"),
        ),
    )
    block_id = connection.execute(
        "SELECT block_id FROM training_blocks WHERE name = ? AND starts_on = ?",
        (block["name"], block["starts_on"]),
    ).fetchone()[0]
    counts = {"training_blocks": 1, "plan_weeks": 0, "plan_sessions": 0, "plan_items": 0}
    for week in payload.get("weeks") or []:
        connection.execute(
            """
            INSERT INTO plan_weeks(
                block_id, starts_on, ends_on, objective, target_distance_m, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(block_id, starts_on) DO UPDATE SET
                ends_on = excluded.ends_on,
                objective = excluded.objective,
                target_distance_m = excluded.target_distance_m,
                status = excluded.status
            """,
            (
                block_id, week["starts_on"], week["ends_on"], week.get("objective"),
                week.get("target_distance_m"), week.get("status") or "planned",
            ),
        )
        week_id = connection.execute(
            "SELECT week_id FROM plan_weeks WHERE block_id = ? AND starts_on = ?",
            (block_id, week["starts_on"]),
        ).fetchone()[0]
        counts["plan_weeks"] += 1
        for session in week.get("sessions") or []:
            connection.execute(
                """
                INSERT INTO plan_sessions(
                    week_id, planned_date, session_type, title, status,
                    target_distance_m, target_duration_s, intensity, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(week_id, planned_date, title) DO UPDATE SET
                    session_type = excluded.session_type,
                    status = excluded.status,
                    target_distance_m = excluded.target_distance_m,
                    target_duration_s = excluded.target_duration_s,
                    intensity = excluded.intensity,
                    notes = excluded.notes
                """,
                (
                    week_id, session["planned_date"], session["session_type"], session["title"],
                    session.get("status") or "planned", session.get("target_distance_m"),
                    session.get("target_duration_s"), session.get("intensity"), session.get("notes"),
                ),
            )
            session_id = connection.execute(
                "SELECT session_id FROM plan_sessions WHERE week_id = ? AND planned_date = ? AND title = ?",
                (week_id, session["planned_date"], session["title"]),
            ).fetchone()[0]
            counts["plan_sessions"] += 1
            for sequence, item in enumerate(session.get("items") or [], 1):
                sequence_no = item.get("sequence_no") or sequence
                connection.execute(
                    """
                    INSERT INTO plan_items(
                        session_id, sequence_no, item_type, target_distance_m,
                        target_duration_s, intensity, instructions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, sequence_no) DO UPDATE SET
                        item_type = excluded.item_type,
                        target_distance_m = excluded.target_distance_m,
                        target_duration_s = excluded.target_duration_s,
                        intensity = excluded.intensity,
                        instructions = excluded.instructions
                    """,
                    (
                        session_id, sequence_no, item.get("item_type") or "segment",
                        item.get("target_distance_m"), item.get("target_duration_s"),
                        item.get("intensity"), item["instructions"],
                    ),
                )
                counts["plan_items"] += 1
    counts["block_id"] = block_id
    return counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create or migrate the private database schema")
    sub.add_parser("verify", help="Run integrity checks and print record counts")
    migration = sub.add_parser("migrate-legacy", help="Import the existing Markdown and recovery JSON")
    migration.add_argument("--dry-run", action="store_true")
    sub.add_parser("cutover", help="Migrate, verify, archive legacy sources, and render compact Markdown")
    render = sub.add_parser("render", help="Regenerate compact Markdown projections")
    render.add_argument("--document", choices=("all", "recovery", "profile", "plan"), default="all")
    context = sub.add_parser("context", help="Read current database context as JSON")
    context.add_argument("--section", choices=("all", "recovery", "profile", "plan"), default="all")
    context.add_argument("--days", type=int, default=14)
    history = sub.add_parser("history", help="Read date-bounded historical records as JSON")
    history.add_argument("--kind", choices=("recovery", "activities", "summaries", "adjustments", "profile"), required=True)
    history.add_argument("--start-date")
    history.add_argument("--end-date")
    history.add_argument("--limit", type=int, default=100)
    recovery = sub.add_parser("upsert-recovery", help="Upsert one recovery entry from a JSON object")
    recovery.add_argument(
        "--input",
        default="-",
        help="JSON file path; defaults to stdin (-)",
    )
    profile = sub.add_parser("set-profile-section", help="Version and replace one current profile section")
    profile.add_argument("--section", required=True)
    profile.add_argument("--value-file", required=True)
    profile.add_argument("--effective-on", default=date.today().isoformat())
    profile.add_argument("--source-ref")
    measurement = sub.add_parser("record-profile-measurement", help="Upsert one profile measurement from JSON")
    measurement.add_argument("--input", required=True)
    event = sub.add_parser("upsert-event", help="Upsert an event from JSON")
    event.add_argument("--input", required=True)
    summary = sub.add_parser("record-summary", help="Upsert a training summary from JSON")
    summary.add_argument("--input", required=True)
    activity = sub.add_parser("record-activity", help="Upsert an activity review from JSON")
    activity.add_argument("--input", required=True)
    plan = sub.add_parser("upsert-plan", help="Upsert a training block and its weeks, sessions, and items from JSON")
    plan.add_argument("--input", required=True)
    plan_section = sub.add_parser("set-plan-section", help="Append a current plan section and regenerate the plan")
    plan_section.add_argument("--section", required=True)
    plan_section.add_argument("--value-file", required=True)
    plan_section.add_argument("--adjusted-at", default=utc_now())
    plan_section.add_argument("--source-ref")
    adjustment = sub.add_parser("record-plan-adjustment", help="Append a plan adjustment from JSON")
    adjustment.add_argument("--input", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.project_root).expanduser().resolve()
    try:
        require_project(root)
        if args.command == "migrate-legacy" and args.dry_run:
            connection = sqlite3.connect(":memory:")
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            apply_migrations(connection)
            report = import_legacy(root, connection)
            report["verification"] = verify_database(connection, report["source_recovery_entries"])
            print(json.dumps(report, indent=2, default=str))
            return 0
        readonly = args.command in {"context", "history"}
        connection = connect(root, readonly=readonly)
        if not readonly:
            applied = apply_migrations(connection)
        else:
            applied = []
        if args.command == "init":
            print(json.dumps({"database": str(database_path(root)), "migrations_applied": applied}, indent=2))
        elif args.command == "verify":
            print(json.dumps(verify_database(connection), indent=2, default=str))
        elif args.command == "migrate-legacy":
            report = import_legacy(root, connection)
            report["verification"] = verify_database(connection, report["source_recovery_entries"])
            print(json.dumps(report, indent=2, default=str))
        elif args.command == "cutover":
            report = import_legacy(root, connection)
            report["verification"] = verify_database(connection, report["source_recovery_entries"])
            archive, manifest = archive_sources(root)
            render_all(root, connection)
            report["archive"] = str(archive)
            report["archive_manifest"] = manifest
            print(json.dumps(report, indent=2, default=str))
        elif args.command == "render":
            if args.document in ("all", "recovery"):
                render_recovery(root, connection)
            if args.document in ("all", "profile"):
                render_profile(root, connection)
            if args.document in ("all", "plan"):
                render_plan(root, connection)
            connection.commit()
            print(json.dumps({"rendered": args.document}, indent=2))
        elif args.command == "context":
            print(json.dumps(context_payload(connection, args.section, args.days), indent=2, default=str))
        elif args.command == "history":
            print(json.dumps(history_payload(connection, args.kind, args.start_date, args.end_date, args.limit), indent=2, default=str))
        elif args.command == "upsert-recovery":
            result = upsert_recovery_entry(connection, load_json_input(args.input))
            connection.commit()
            render_recovery(root, connection)
            print(json.dumps(result, indent=2))
        elif args.command == "set-profile-section":
            value = Path(args.value_file).read_text(encoding="utf-8").strip()
            set_profile_section(connection, args.section, value, args.effective_on, args.source_ref)
            connection.commit()
            render_profile(root, connection)
            print(json.dumps({"updated": args.section}, indent=2))
        elif args.command == "record-profile-measurement":
            payload = load_json_input(args.input)
            record_profile_measurement(connection, payload)
            connection.commit()
            print(json.dumps({"recorded": payload["metric_key"]}, indent=2))
        elif args.command == "upsert-event":
            payload = load_json_input(args.input)
            event_id = upsert_event_payload(connection, payload)
            connection.commit()
            print(json.dumps({"event_id": event_id}, indent=2))
        elif args.command == "record-summary":
            payload = load_json_input(args.input)
            summary_id = record_summary_payload(connection, payload)
            connection.commit()
            print(json.dumps({"summary_id": summary_id}, indent=2))
        elif args.command == "record-activity":
            payload = load_json_input(args.input)
            activity_date = str(payload.get("started_at") or payload.get("date") or "")[:10]
            upsert_activity_from_mapping(connection, activity_date, payload)
            connection.commit()
            print(json.dumps({"recorded": payload.get("activity_id") or payload.get("activity_file")}, indent=2))
        elif args.command == "upsert-plan":
            result = upsert_plan_payload(connection, load_json_input(args.input))
            connection.commit()
            print(json.dumps(result, indent=2))
        elif args.command == "set-plan-section":
            record_plan_adjustment(connection, {
                "adjusted_at": args.adjusted_at,
                "reason": args.section,
                "decision": Path(args.value_file).read_text(encoding="utf-8").strip(),
                "source_type": "agent",
                "source_ref": args.source_ref,
            })
            connection.commit()
            render_plan(root, connection)
            print(json.dumps({"updated": args.section}, indent=2))
        elif args.command == "record-plan-adjustment":
            record_plan_adjustment(connection, load_json_input(args.input))
            connection.commit()
            render_plan(root, connection)
            print(json.dumps({"recorded": True}, indent=2))
        connection.close()
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
