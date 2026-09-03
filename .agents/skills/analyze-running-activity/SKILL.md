---
name: analyze-running-activity
description: Retrieve and confirm a completed running activity, derive its private route location, fetch historical weather, collect missing qualitative context, and analyze it against the active running plan and development goals. Use when the user asks to sync or review the latest Garmin run; provides a Garmin or Strava FIT/GPX file, activity screenshot, splits, pace/HR/cadence/power data, or subjective run report; or asks for physiological interpretation, next-seven-day adjustment, or a durable training-record update. When GarminDB is connected, perform an incremental activity sync before selecting the run.
---

# Analyze Running Activity

## Goal

Retrieve and resolve the intended run, derive a privacy-limited location and historical weather record, combine its objective data with missing qualitative context, and determine whether the active plan or athlete model should change. Ask the user to identify the activity only when the available evidence is genuinely ambiguous.

## Required Gated Workflow

Do not produce the analysis before the target activity is resolved and the available qualitative context is collected. Resolve an unambiguous activity automatically; require user confirmation only for an ambiguous or conflicting match. If the user supplies the missing context in the original request, continue without asking again.

### 1. Sync GarminDB When Connected

Treat GarminDB as connected when all of these exist:

- `docs/garmindb/GarminConnectConfig.json`
- `.venv/bin/garmindb_cli.py` on macOS/Linux, or the equivalent executable under `.venv\Scripts\` on Windows
- `docs/garmindb/data/`

When connected, run the guarded incremental activity-only sync from the project root:

```bash
python3 .agents/skills/analyze-running-activity/scripts/sync_latest_garmindb.py \
  --project-root . --json
```

Do this at the start of every run-analysis request unless the user explicitly requests an offline/no-sync analysis. The wrapper owns the GarminDB working directory, command arguments, overlap protection, error classification, and post-sync database verification. Do not reconstruct or bypass its underlying command.

- For `status: success`, continue to activity selection. `fresh_data_imported: false` means the sync succeeded but found no newer activity.
- For `status: failed`, report its category and message, then ask whether to continue from the last local import or a user-supplied file.
- For `status: busy`, wait for the existing sync rather than starting another.
- For `status: not_connected`, use a user-supplied source.

Keep logs, tokens, downloaded files, and databases under `docs/`. Do not print credentials, tokens, route coordinates, configuration contents, or the raw private log. Do not silently present stale data as freshly synced.

When GarminDB is not connected, use the FIT/GPX file, screenshot, summary, or written data supplied by the user. If no usable activity source exists, ask for one.

### 2. Identify and Resolve the Activity

After a successful sync, or when continuing from the existing local database, list recent running candidates:

```bash
python3 .agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py --project-root . --limit 5
```

When the user supplied a date, query that date explicitly:

```bash
python3 .agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py \
  --project-root . --date YYYY-MM-DD --limit 20 --json
```

Confirm that the requested date has a matching activity before parsing. Resolve relative dates such as `today` and `yesterday` to an explicit local date. Match a user-specified time, title, distance, or activity ID when provided; otherwise select the newest running activity as the candidate. Do not silently substitute an activity from another date.

Check the reported lap, record, GPS-record, and split row counts. A GarminDB summary row does not prove that detailed activity data imported successfully. Prefer the corresponding FIT file over the database summary; when the FIT file is missing and detail rows are incomplete, label the objective record as partial.

For a FIT candidate, invoke `parse-fit-run`:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py path/to/activity.fit --json
```

Treat the activity as resolved without asking when either condition holds:

- the user supplied the activity file or activity ID and its parsed date does not conflict with the request;
- exactly one running activity exists on the explicit requested local date, and its available time, distance, title, and supplied context do not materially conflict with the request.

For an automatically resolved activity, continue directly and include the identity summary in the final analysis. Do not ask the user to validate an internal activity ID or repeat that a sole same-day run is theirs.

Ask the user to choose or clarify only when multiple plausible activities exist, the activity date differs from the requested date, supplied details conflict materially with the candidate, or no date/source makes the newest activity uncertain. Present a compact identity summary for only the plausible candidates using local start date/time, title when useful, distance, duration, saved Garmin feel/effort when present, detail coverage, and activity ID. Never show route coordinates. Wait for the answer before analyzing an ambiguous activity.

### 3. Retrieve Location and Historical Weather

After resolving the activity, retrieve weather automatically when FIT, GPX, or GarminDB GPS records are available:

```bash
python3 .agents/skills/analyze-running-activity/scripts/fetch_historical_weather.py \
  --project-root . --activity-id ACTIVITY_ID --json
```

For a directly supplied file, use `--activity-file docs/activities/FILE.fit` (or `.gpx`) instead of `--activity-id`.

The helper derives a representative route point, quantizes it to a 0.05-degree grid before the request, queries the Open-Meteo Historical Weather API for the activity window, and omits coordinates from all output. It returns temperature, apparent temperature, humidity, dew point, precipitation, wind, gusts, and weather codes with provenance and limitations. Attribute Open-Meteo when using the result in the report. Do not print coordinates, retain the request URL, reverse-geocode a home or route, or write coordinates into `running_data.db`.

Treat historical weather as a gridded estimate rather than an on-route measurement. It may miss localized shade, sun, gusts, precipitation, or rapid changes. If the activity lacks usable GPS/timestamps or the service is unavailable, state that automatic weather retrieval was unavailable and continue. Ask the user about weather only when that missing uncertainty would materially change the interpretation; do not routinely shift weather entry back to the user.

### 4. Collect Missing Qualitative Context

After the activity is resolved, begin any needed question with the explicit activity date—for example, “For the run on `YYYY-MM-DD`…”—and ask only for information the activity data, current conversation, and private record do not already provide:

- intended purpose or assigned session;
- perceived effort and breathing/talk-test experience;
- pain or unusual discomfort during, immediately after, and the next morning, including any gait change;
- fatigue or soreness before and after;
- terrain, surface, footing, or unusual localized exposure not established by the activity and weather data;
- fueling and hydration when relevant;
- stops, interruptions, equipment issues, or suspected sensor errors.

Treat GarminDB `self_eval_effort` and `self_eval_feel` as user-entered subjective evidence. Use their labels verbatim and do not convert them to a numeric RPE without a documented mapping. Do not ask the user to repeat perceived effort when a saved label is present unless the user supplied a conflicting description or clarification would materially affect the analysis. A current written report overrides a stale or accidental saved label; preserve and explain a material conflict.

Keep the question batch short, allow `unknown` or `not applicable`, and wait for the reply. Ask whether there is pain or soreness now or the next morning only when that timing is applicable. Do not infer breathing, pain, fatigue, or other subjective experience from pace, HR, Garmin labels, or the saved effort/feel fields.

### 5. Read the Private Athlete Record

Before analysis, read:

- `docs/runner_profile.md`
- `docs/running_plan.md`
- `docs/recovery_metrics.md` when recovery or recent symptoms affect interpretation
- the relevant current or historical rows from `docs/running_data.db` when the compact projections do not contain enough context. Use `manage_running_data.py context` for current state and a date-bounded `history` query for older recovery, activities, summaries, adjustments, or profile entries.

Never substitute root example files.

### 6. Build the Objective Record

1. Prefer original FIT/GPX data over screenshots, database summaries, or activity labels.
2. Use parsed local start time and record-derived distance, timer time, pace, HR, cadence, power, HR-zone distribution, splits, and first-half/second-half comparison.
3. Treat GarminDB, session, and lap summaries as supporting evidence when record-derived values are available.
4. State what is missing, unreliable, or inconsistent. Flag GPS errors, wrist-HR artifacts, cadence lock, pauses, incomplete sensor coverage, and unusable elapsed pace.
5. Add the historical-weather summary and its limitations when retrieval succeeded. Use apparent temperature, humidity/dew point, precipitation, wind, and gusts when they materially affect effort or pacing interpretation.
6. Combine device data and historical weather with the confirmed qualitative context.

### 7. Analyze the Session

- Compare the actual work with the assigned purpose.
- Distinguish purpose from intensity:
  - a recovery run is deliberately low cost;
  - an easy aerobic run is developmental volume;
  - an easy long run is a major durability stimulus;
  - a short run can still be moderate or hard.
- Evaluate pacing discipline, HR behavior, cadence/form indicators, aerobic efficiency, durability, and recovery cost.
- Interpret wrist HR with pace, breathing, RPE, heat, terrain, mechanics, and possible cadence lock. Do not use an approximate HR boundary as an automatic stop signal.
- Classify symptoms precisely:
  - stable mild discomfort resolving within hours and absent the next morning is a monitoring signal;
  - recurrence, increasing severity, morning symptoms, swelling, focal bone/tendon pain, altered gait, or worsening during the run is stronger warning evidence.
- Do not diagnose an injury.

### 8. Update the Plan and Durable Files

- Read `.agents/running_data/CONTRACT.md` before preparing database writes.
- Record every completed analysis in `activity_reviews`, even when it does not change the athlete model or plan. Prepare a private JSON object with `source_activity_id`, `started_at`, typed summary fields, `outcome`, the retrieved weather object under `details.weather` when available, and any other uncommon evidence in the remaining object, then run:

  ```bash
  python3 .agents/scripts/manage_running_data.py --project-root . \
    record-activity --input docs/tmp/activity-review.json
  ```

- Decide whether the next run should be kept, modified, or skipped.
- Check the next 7 days for both injury/under-recovery risk and undertraining risk.
- Give any restriction a reason, exit criteria, and reassessment point.
- Update normalized plan rows and append a plan adjustment when the activity materially changes the remaining week, mileage target, next workout, long run, recovery need, symptom handling, or progress toward the current development objective. Regenerate the compact plan through the shared manager.
- Version the relevant current profile section or add a measurement when the activity materially changes the athlete model, zones, durability, pacing/HR interpretation, strengths, weaknesses, or risk. Regenerate the compact profile through the shared manager.
- Do not add an incomplete week to `training_summaries`; close it during a weekly review.
- If the run is a one-off observation and the active plan remains correct, record only the activity review.
- Remove private temporary JSON or section files after verifying the database write.

### 9. Return the Analysis Report

Use exactly:

```text
A. Verdict
B. What the run was supposed to accomplish
C. What actually happened
D. What was good
E. What was poor or concerning
F. Physiological interpretation
G. Impact on running plan
H. Adjustment to next 7 days
I. One clear takeaway
J. Durable file updates
```

In section J, state which database records were written, whether `docs/runner_profile.md` or `docs/running_plan.md` was regenerated, and why.
