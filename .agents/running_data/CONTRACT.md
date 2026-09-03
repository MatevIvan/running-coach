# Running Data Contract

`docs/running_data.db` is the durable historical record. The Markdown files under `docs/` are compact current-context projections. Write the database first and regenerate the affected projection with `.agents/scripts/manage_running_data.py`.

Pass one-off JSON payloads through standard input when a command supports it. If a JSON input file is specifically useful, keep it private under `docs/tmp/` and remove it after a successful write. Distances use meters, durations use seconds, paces use seconds per kilometer, and dates use `YYYY-MM-DD`. Timestamps use ISO 8601.

## GarminDB Projection Boundary

GarminDB remains the complete read-only upstream source for downloaded activity, monitoring, sleep, HRV, and daily-summary data. Do not mirror its raw tables, route points, records, laps, splits, monitoring samples, credentials, or tokens into `docs/running_data.db`.

Project only coaching-ready evidence into this database:

- normalized recent daily recovery rows belong in `recovery_daily`, with exact-date provenance and missing fields preserved;
- reviewed weekly or monthly aggregates belong in `training_summaries`;
- durable conclusions and dated measurements belong in `profile_entries` and `profile_measurements`;
- an individual run belongs in `activity_reviews` only after the activity-analysis workflow has produced a coaching interpretation with the required qualitative context.

During initialization, default to the most recent 28 valid recovery days, up to 90 when needed for a material baseline or trend, the most recent 12 complete weekly training summaries, and useful monthly summaries for older imported history. GarminDB remains queryable for older or more granular objective evidence.

## Read commands

```bash
python3 .agents/scripts/manage_running_data.py --project-root . context --section all --days 14
python3 .agents/scripts/manage_running_data.py --project-root . history --kind activities --start-date YYYY-MM-DD --end-date YYYY-MM-DD
python3 .agents/scripts/manage_running_data.py --project-root . verify
```

`history --kind` accepts `recovery`, `activities`, `summaries`, `adjustments`, or `profile`.

## Recovery input

Use the existing recovery-entry field names so device wording and provenance remain lossless in `details_json`:

```json
{
  "date": "YYYY-MM-DD",
  "sleep_duration": "7h 15min",
  "sleep_duration_minutes": 435,
  "sleep_score": 80,
  "resting_hr_bpm": 48,
  "hrv": {"value_ms": 58, "seven_day_average_ms": 56, "status": "balanced"},
  "training_readiness": {"score": 72},
  "body_battery_stress": {"body_battery": {"daily_high": 85}, "stress": {"avg": 24}},
  "soreness_or_pain": "None.",
  "illness_or_fatigue": "None.",
  "notes": "Current interpretation and training implication.",
  "source": "User report and exact-date GarminDB verification"
}
```

```bash
python3 .agents/scripts/manage_running_data.py --project-root . upsert-recovery
```

`upsert-recovery` reads the JSON object from stdin by default. Use `--input PATH` only when a file-backed payload is specifically useful; `--input -` is an explicit synonym for stdin.

## Activity-review input

```json
{
  "source_activity_id": "garmin:ACTIVITY_ID",
  "started_at": "YYYY-MM-DDTHH:MM:SS-07:00",
  "distance_m": 5000,
  "duration_s": 1800,
  "avg_hr_bpm": 145,
  "avg_pace_sec_per_km": 360,
  "rpe": 3,
  "outcome": "Concise durable interpretation.",
  "details": {
    "sensor_limits": "Optional uncommon audit detail",
    "weather": {
      "source": "Open-Meteo Historical Weather API",
      "conditions": "Weather summary returned by fetch_historical_weather.py",
      "location": {"coordinates_withheld": true}
    }
  }
}
```

```bash
python3 .agents/scripts/manage_running_data.py --project-root . record-activity --input docs/tmp/activity-review.json
```

## Profile writes

Write a complete Markdown section body to a private temporary text file, then version it:

```bash
python3 .agents/scripts/manage_running_data.py --project-root . set-profile-section \
  --section "Runner Profile" --value-file docs/tmp/profile-section.md \
  --effective-on YYYY-MM-DD --source-ref SOURCE_REFERENCE
```

Measurement input:

```json
{
  "measured_on": "YYYY-MM-DD",
  "metric_key": "weight_lb",
  "value_num": 140,
  "source_type": "athlete_report",
  "source_ref": "brief source description"
}
```

Use a metric key that includes its canonical unit.

## Event input

```json
{
  "name": "Event name",
  "event_date": "YYYY-MM-DD",
  "event_type": "marathon",
  "distance_m": 42195,
  "priority": "completion",
  "status": "tentative",
  "notes": "Only confirmed or explicitly tentative context."
}
```

## Plan input

```json
{
  "replace_active": true,
  "block": {
    "name": "Block name",
    "objective": "Measurable objective",
    "starts_on": "YYYY-MM-DD",
    "ends_on": "YYYY-MM-DD",
    "status": "active",
    "reassess_on": "YYYY-MM-DD"
  },
  "weeks": [
    {
      "starts_on": "YYYY-MM-DD",
      "ends_on": "YYYY-MM-DD",
      "objective": "Weekly objective",
      "target_distance_m": 24000,
      "status": "active",
      "sessions": [
        {
          "planned_date": "YYYY-MM-DD",
          "session_type": "easy_run",
          "title": "Easy run",
          "status": "planned",
          "target_distance_m": 5000,
          "intensity": "Conversational",
          "notes": "Execution and stop conditions",
          "items": [
            {"sequence_no": 1, "item_type": "continuous", "instructions": "Run easily."}
          ]
        }
      ]
    }
  ]
}
```

Use `upsert-plan` for structure. Use `set-plan-section` for a complete compact Markdown section. Use `record-plan-adjustment` for a dated decision; omit `target_type` and `target_id` to target the active block automatically.

## Training-summary input

```json
{
  "period_type": "week",
  "starts_on": "YYYY-MM-DD",
  "ends_on": "YYYY-MM-DD",
  "run_count": 4,
  "distance_m": 24000,
  "duration_s": 9000,
  "load_value": null,
  "key_takeaway": "Concise reviewed conclusion.",
  "details": {"coverage": "Complete"}
}
```

Run `verify` after a multi-record update. Never write directly to GarminDB; it remains a separate read-only upstream source.
