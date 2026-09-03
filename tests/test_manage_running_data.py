from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agents" / "scripts" / "manage_running_data.py"
SPEC = importlib.util.spec_from_file_location("manage_running_data", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


PROFILE = """# Runner Profile

Last updated: 2026-01-08

## Athlete Baseline

- Age: 30
- Height: 5 ft 6 in
- Weight used for planning: about 140 lb
- Garmin resting HR estimate: 47 bpm
- Garmin max HR estimate: 198 bpm
- Garmin VO2 max estimate: 54
- Garmin running lactate-threshold estimate: 179 bpm, 7:09/mi, 324 W, 5.21 W/kg

## Goals and Event Context

- Active event context: use Example Marathon on Sunday 2026-03-01 as a tentative planning anchor.

## Data Processed

Legacy source notes that should move out of the compact profile.

## Facts Supported by Running Data

| Month | Runs | Miles | Longest Run |
|---|---:|---:|---:|
| 2026-01 | 3 | 9.0 | 4.0 mi |

| Week Starting | Runs | Miles | Long Run | Avg HR | Relative Effort |
|---|---:|---:|---:|---:|---:|
| 2026-01-05 | 2 | 6.0 | 3.0 | 140 | 20 |

- 2026-01-07: 3.0 mi in 30:00 at 10:00/mi, average HR 140. Easy and symptom-free.

## Estimates and Open Inputs

- Confirm future availability.

## Runner Profile

- Consistency is the current limiter.

## Training Zones and Pacing

### Heart-Rate Zones

| Zone | Heart Rate | Purpose |
|---|---:|---|
| Z1 | <135 bpm | Recovery |

## Active Running Plan

See `docs/running_plan.md`.

## Future Chats Should Know

Historical detail that is intentionally omitted from the compact projection.
"""


PLAN = """# Running Plan

Last updated: 2026-01-08

## Plan Status

- Primary development objective: build consistent easy volume.
- Current development block: Base Build, 2026-01-05 through 2026-02-01.
- Development review points: reassess on 2026-01-26.
- Active event context: use Example Marathon on Sunday 2026-03-01 as a tentative planning anchor.

## Previous Week

Week: 2025-12-29 to 2026-01-04.

Operating goal: establish a baseline.

| Day | Session | Distance / Time | Pace / HR Target | Notes |
|---|---|---:|---|---|
| Sat 2026-01-03 | Completed easy run | 3 mi | Conversational | No issues. |

## This Week's Plan

Week: 2026-01-05 to 2026-01-11.

- Target: 9 mi across three runs.

| Day | Session | Distance / Time | Pace / HR Target | Notes |
|---|---|---:|---|---|
| Mon 2026-01-05 | Easy run | 3 mi | Conversational | Stop for pain. |
| Wed 2026-01-07 | Completed easy run | 3 mi | Conversational | Completed normally. |
| Sat 2026-01-10 | Long easy run | 3 mi | Conversational | Keep it easy. |

## Planning Assumptions

- Three available running days.

## Training Intensity Rules

- Keep easy runs conversational.

## Current 7-Day Adjustment

Old detailed adjustment history that should leave the compact plan.

## Development Horizon and Conditional Event Build

- Reassess before progressing.

## Adjustment Rules

- Do not make up missed mileage.

## Questions to Resolve

- Confirm schedule.
"""


RECOVERY = {
    "schema_version": 1,
    "last_updated": "2026-01-08",
    "entries": [
        {
            "date": "2026-01-07",
            "sleep_duration": "7h 30min",
            "sleep_duration_minutes": 450,
            "sleep_score": 80,
            "resting_hr_bpm": 47,
            "hrv": {"value_ms": 58, "seven_day_average_ms": 56, "status": "balanced"},
            "training_readiness": {"score": 72},
            "body_battery_stress": {"body_battery": {"daily_high": 85}, "stress": {"avg": 24}},
            "soreness_or_pain": "None.",
            "notes": "Normal recovery.",
            "source": "User daily metrics",
            "run_response": {
                "activity_id": 123,
                "distance_miles": 3.0,
                "duration": "30:00",
                "average_hr_bpm": 140,
                "pace": "10:00/mi",
                "interpretation": "Easy and symptom-free.",
            },
        },
        {
            "date": "2026-01-08",
            "sleep_duration": "6h 45min",
            "sleep_duration_minutes": 405,
            "sleep_score": 70,
            "resting_hr_bpm": 49,
            "hrv": {"value_ms": 52, "status": "balanced"},
            "training_readiness": {"score": 60},
            "body_battery_stress": {"body_battery": {"daily_high": 70}, "stress": {"avg": 30}},
            "soreness_or_pain": "Mild generalized soreness.",
            "illness_or_fatigue": "No illness.",
            "notes": "Keep training easy.",
            "source": "GarminDB and user report",
        },
    ],
}


class RunningDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "AGENTS.md").write_text("test\n", encoding="utf-8")
        docs = self.root / "docs"
        docs.mkdir()
        (docs / "runner_profile.md").write_text(PROFILE, encoding="utf-8")
        (docs / "running_plan.md").write_text(PLAN, encoding="utf-8")
        (docs / "recovery_metrics.md").write_text("# Recovery Metrics\n\nLegacy rolling view.\n", encoding="utf-8")
        (docs / "recovery_metrics_raw.json").write_text(json.dumps(RECOVERY), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_schema_import_idempotency_and_projections(self) -> None:
        connection = MODULE.connect(self.root)
        self.assertEqual(MODULE.apply_migrations(connection), [1])
        first = MODULE.import_legacy(self.root, connection)
        verified = MODULE.verify_database(connection, expected_recovery=2)
        self.assertEqual(verified["integrity_check"], "ok")
        self.assertEqual(verified["counts"]["recovery_daily"], 2)
        self.assertEqual(first["source_recovery_entries"], 2)

        table_count = connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        self.assertEqual(table_count, 13)

        before = verified["counts"]
        MODULE.import_legacy(self.root, connection)
        after = MODULE.verify_database(connection, expected_recovery=2)["counts"]
        self.assertEqual(before, after)

        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO plan_adjustments(adjusted_at, reason, decision, source_type) VALUES ('2026-01-08', 'x', 'y', 'test')"
            )
        connection.rollback()

        MODULE.render_all(self.root, connection)
        compact_profile = (self.root / "docs" / "runner_profile.md").read_text(encoding="utf-8")
        compact_plan = (self.root / "docs" / "running_plan.md").read_text(encoding="utf-8")
        compact_recovery = (self.root / "docs" / "recovery_metrics.md").read_text(encoding="utf-8")
        self.assertNotIn("## Data Processed", compact_profile)
        self.assertNotIn("## Current 7-Day Adjustment", compact_plan)
        self.assertIn("docs/running_data.db", compact_recovery)
        connection.close()

    def test_archive_is_checksum_verified_and_recoverable(self) -> None:
        original_hash = MODULE.sha256_file(self.root / "docs" / "recovery_metrics_raw.json")
        archive, manifest = MODULE.archive_sources(self.root)
        self.assertFalse((self.root / "docs" / "recovery_metrics_raw.json").exists())
        self.assertEqual(MODULE.sha256_file(archive / "recovery_metrics_raw.json"), original_hash)
        self.assertEqual(manifest["files"]["recovery_metrics_raw.json"]["sha256"], original_hash)
        self.assertTrue((archive / "manifest.json").is_file())

    def test_current_write_interfaces(self) -> None:
        connection = MODULE.connect(self.root)
        MODULE.apply_migrations(connection)
        MODULE.import_legacy(self.root, connection)

        MODULE.set_profile_section(connection, "Runner Profile", "First version.", "2026-01-08", "test:profile:1")
        MODULE.set_profile_section(connection, "Runner Profile", "Corrected version.", "2026-01-08", "test:profile:2")
        current = connection.execute(
            "SELECT value_text FROM v_current_profile WHERE entry_key = 'profile-section:runner-profile'"
        ).fetchall()
        self.assertEqual([row[0] for row in current], ["Corrected version."])

        event_id = MODULE.upsert_event_payload(connection, {
            "name": "Confirmed 10K",
            "event_date": "2026-04-01",
            "event_type": "road_race",
            "distance_m": 10000,
            "status": "confirmed",
        })
        plan_result = MODULE.upsert_plan_payload(connection, {
            "replace_active": True,
            "block": {
                "event_id": event_id,
                "name": "10K Build",
                "objective": "Build repeatable threshold volume.",
                "starts_on": "2026-02-01",
                "ends_on": "2026-03-29",
                "status": "active",
                "reassess_on": "2026-02-22",
            },
            "weeks": [{
                "starts_on": "2026-02-02",
                "ends_on": "2026-02-08",
                "status": "planned",
                "sessions": [{
                    "planned_date": "2026-02-03",
                    "session_type": "easy_run",
                    "title": "Easy run",
                    "items": [{"item_type": "continuous", "instructions": "Run conversationally."}],
                }],
            }],
        })
        self.assertEqual(plan_result["plan_sessions"], 1)
        MODULE.record_plan_adjustment(connection, {
            "reason": "Schedule change",
            "decision": "Move the easy run one day.",
            "source_ref": "test:adjustment:1",
        })
        MODULE.record_summary_payload(connection, {
            "period_type": "week",
            "starts_on": "2026-02-02",
            "ends_on": "2026-02-08",
            "run_count": 3,
            "distance_m": 15000,
            "key_takeaway": "Completed as planned.",
        })
        MODULE.upsert_activity_from_mapping(connection, "2026-02-03", {
            "source_activity_id": "test:activity:1",
            "started_at": "2026-02-03T07:00:00-08:00",
            "distance_m": 5000,
            "duration_s": 1800,
            "avg_hr_bpm": 145,
            "avg_pace_sec_per_km": 360,
            "rpe": 3,
            "outcome": "Controlled easy run.",
        })
        connection.commit()
        verified = MODULE.verify_database(connection)
        self.assertEqual(verified["integrity_check"], "ok")
        self.assertEqual(
            connection.execute("SELECT distance_m FROM activity_reviews WHERE source_activity_id = 'test:activity:1'").fetchone()[0],
            5000,
        )


if __name__ == "__main__":
    unittest.main()
