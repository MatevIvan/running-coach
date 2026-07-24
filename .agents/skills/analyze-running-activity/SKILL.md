---
name: analyze-running-activity
description: Retrieve and confirm a completed running activity, collect missing qualitative context, and analyze it against the active marathon plan. Use when the user asks to sync or review the latest Garmin run; provides a Garmin or Strava FIT/GPX file, activity screenshot, splits, pace/HR/cadence/power data, or subjective run report; or asks for physiological interpretation, next-seven-day adjustment, or a durable training-record update. When GarminDB is connected, perform an incremental activity sync before selecting the run.
---

# Analyze Running Activity

## Goal

Retrieve the intended run, verify its identity with the user, combine its objective data with missing qualitative context, and determine whether the active plan or athlete model should change.

## Required Gated Workflow

Do not collapse these gates or produce the analysis before the target activity is confirmed and the available qualitative context is collected. If the user confirms the activity and supplies the missing context in one reply, continue without asking again.

### 1. Sync GarminDB When Connected

Treat GarminDB as connected when all of these exist:

- `docs/garmindb/GarminConnectConfig.json`
- `.venv/bin/garmindb_cli.py` on macOS/Linux, or the equivalent executable under `.venv\Scripts\` on Windows
- `docs/garmindb/data/`

When connected, run the incremental activity-only sync from `docs/garmindb/` before selecting an activity:

```bash
../../.venv/bin/garmindb_cli.py --config . --activities --download --import --analyze --latest
```

Do this at the start of every run-analysis request unless the user explicitly requests an offline/no-sync analysis. Keep logs, tokens, downloaded files, and databases under `docs/`. Do not print credentials, tokens, route coordinates, or configuration contents. Wait for the command to finish and do not start a duplicate import.

If authentication, MFA, network access, or the import fails, report the failure precisely and ask whether to continue from the last local import or a user-supplied file. Do not silently present stale data as freshly synced.

When GarminDB is not connected, use the FIT/GPX file, screenshot, summary, or written data supplied by the user. If no usable activity source exists, ask for one.

### 2. Identify and Confirm the Activity

After a successful sync, or when continuing from the existing local database, list recent running candidates:

```bash
python3 .agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py --project-root . --limit 5
```

When the user supplied a date, query that date explicitly:

```bash
python3 .agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py \
  --project-root . --date YYYY-MM-DD --limit 20 --json
```

Confirm that the requested date has a matching activity before parsing. Match a user-specified time, title, distance, or activity ID when provided; otherwise select the newest running activity as the candidate. Do not silently substitute an activity from another date.

Check the reported lap, record, and split row counts. A GarminDB summary row does not prove that detailed activity data imported successfully. Prefer the corresponding FIT file over the database summary; when the FIT file is missing and detail rows are incomplete, label the objective record as partial.

For a FIT candidate, invoke `parse-fit-run`:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py path/to/activity.fit --json
```

Present a compact identity summary using local start date/time, activity title when useful, distance, duration, detail coverage, and activity ID. Never show route coordinates. Ask the user to confirm that this is the intended activity and wait for the answer. If the match is ambiguous, present only the few plausible candidates. Do not analyze an unconfirmed activity.

### 3. Collect Missing Qualitative Context

After confirmation, begin the question with the explicit activity date—for example, “For the run on `YYYY-MM-DD`…”—and ask only for information the activity data, current conversation, and private record do not already provide:

- intended purpose or assigned session;
- RPE from 1–10 and breathing/talk-test experience;
- pain or unusual discomfort during, immediately after, and the next morning, including any gait change;
- fatigue or soreness before and after;
- material weather, heat, wind, terrain, or surface conditions;
- fueling and hydration when relevant;
- stops, interruptions, equipment issues, or suspected sensor errors.

Keep the question batch short, allow `unknown` or `not applicable`, and wait for the reply. Ask whether there is pain or soreness now or the next morning only when that timing is applicable. Do not infer subjective experience from pace, HR, Garmin labels, or self-evaluation fields alone.

### 4. Read the Private Athlete Record

Before analysis, read:

- `docs/runner_profile.md`
- `docs/marathon_plan.md`
- `docs/recovery_metrics_raw.json` and `docs/recovery_metrics.md` when recovery or recent symptoms affect interpretation

Never substitute root example files.

### 5. Build the Objective Record

1. Prefer original FIT/GPX data over screenshots, database summaries, or activity labels.
2. Use parsed local start time and record-derived distance, timer time, pace, HR, cadence, power, HR-zone distribution, splits, and first-half/second-half comparison.
3. Treat GarminDB, session, and lap summaries as supporting evidence when record-derived values are available.
4. State what is missing, unreliable, or inconsistent. Flag GPS errors, wrist-HR artifacts, cadence lock, pauses, incomplete sensor coverage, and unusable elapsed pace.
5. Combine device data with the confirmed qualitative context.

### 6. Analyze the Session

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

### 7. Update the Plan and Durable Files

- Decide whether the next run should be kept, modified, or skipped.
- Check the next 7 days for both injury/under-recovery risk and undertraining risk.
- Give any restriction a reason, exit criteria, and reassessment point.
- Update `docs/marathon_plan.md` when the activity materially changes the remaining week, mileage target, next workout, long run, recovery need, or symptom handling.
- Update `docs/runner_profile.md` when the activity materially changes the athlete model, zones, durability, pacing/HR interpretation, strengths, weaknesses, or risk.
- Do not add an incomplete week to `Facts Supported by Running Data`; close it during a weekly review.
- If the run is a one-off observation and the active plan remains correct, update neither durable file.

### 8. Return the Analysis Report

Use exactly:

```text
A. Verdict
B. What the run was supposed to accomplish
C. What actually happened
D. What was good
E. What was poor or concerning
F. Physiological interpretation
G. Impact on marathon plan
H. Adjustment to next 7 days
I. One clear takeaway
J. Durable file updates
```

In section J, state whether `docs/runner_profile.md`, `docs/marathon_plan.md`, both, or neither were updated, and why.
