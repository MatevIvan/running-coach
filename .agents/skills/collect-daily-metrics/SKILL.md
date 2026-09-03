---
name: collect-daily-metrics
description: Collect, validate, store, and interpret daily GarminDB, Garmin, or self-reported recovery metrics; reconcile prior-day sleep and Body Battery when GarminDB is connected; and recommend the specific run or rest decision for that day. Use when the user provides or requests sleep duration or score, resting heart rate, HRV value/status/baseline, training readiness, Body Battery, stress, soreness, pain, illness, fatigue, nutrition, or daily recovery screenshots; asks what run to do or whether to train today; or requests an update to the private recovery log.
---

# Collect Daily Metrics

## Goal

Turn daily recovery information into an accurate permanent record, a compact rolling view, and a specific recovery-adjusted run or rest recommendation without overreacting to one metric.

## Read First

Read:

- `.agents/running_data/CONTRACT.md` before writing recovery data
- the latest database recovery context:

  ```bash
  python3 .agents/scripts/manage_running_data.py --project-root . \
    context --section recovery --days 14
  ```

- `docs/recovery_metrics.md`
- `docs/running_plan.md`
- `docs/runner_profile.md` only when baseline, symptoms, or a durable trend matters

Never use root example files as live data.

## GarminDB and Qualitative Gate

Complete this sequence before interpreting recovery or updating files:

1. Resolve and state the current morning metric date as `YYYY-MM-DD`, then calculate the prior calendar date. Current-morning sleep means the sleep session ending that morning.
2. Treat the user's Garmin/watch entry or screenshot as the normal source for the current morning because GarminDB's standard `--latest` download ends on the prior date.
3. When GarminDB is connected, run the guarded recovery sync before reading either date. This is a network operation: request or enable narrowly scoped network access on the first attempt using the current harness's authorization mechanism; do not first run the sync in a network-blocked environment as a probe. If network execution cannot be authorized, report the sync as unavailable and follow the exact-date local-data fallback below without describing the local data as freshly synced.

   ```bash
   python3 .agents/skills/collect-daily-metrics/scripts/sync_latest_garmindb_recovery.py \
     --project-root . --date PRIOR-YYYY-MM-DD --json
   ```

   The wrapper owns the GarminDB working directory, recovery-only command flags, shared sync lock, private output capture, and database/coverage verification. Do not reconstruct or bypass its underlying command.
   - Accept `status: success` only when `sync_completed` and `database_verified` are both `true`. Continue when `coverage_complete` is false, but report the named missing sources.
   - For `status: failed` with category `network`, retry once immediately with network access if the first execution did not have it. Do not interpret stale coverage until that retry finishes.
   - For any other `status: failed`, report its category and use existing data only when exact-date coverage can still be verified.
   - For `status: busy`, wait for the existing GarminDB sync.
   - For `status: not_connected`, continue from user-supplied metrics and state that prior-day verification and Body Battery retrieval are unavailable.
   - Never describe the database as merely stale when the sync failed. Report the failed pull separately from the latest locally available date.

4. Query the prior date read-only:

   ```bash
   python3 .agents/skills/collect-daily-metrics/scripts/read_garmindb_daily.py \
     --project-root . --date PRIOR-YYYY-MM-DD
   ```

   For a trend review, use `--start-date YYYY-MM-DD --end-date YYYY-MM-DD`. Check each source independently, including `sleep`, `resting_hr`, `hrv`, `daily_summary`, and relevant monitoring or summary rows. Do not assume one present row means the day is complete.

5. Reconcile the prior date before analyzing the current morning:
   - confirm its sleep duration and score against the existing prior-date raw entry;
   - merge GarminDB sleep stages, resting HR, overnight/rolling HRV, and source provenance when available;
   - retrieve `bb_max`, `bb_min`, `bb_charged`, stress, steps, and activity time from the prior-date `daily_summary`;
   - keep every prior-day value attached to the prior date, not the current morning;
   - report material conflicts and prefer the more direct objective source without discarding qualitative context.
6. Extract the current morning values supplied by the user. Do not ask the user to repeat prior-date fields already available in GarminDB. Mark current-day wearable fields unavailable when they were neither supplied nor supported by an exact-date source.
7. After objective extraction, ask one concise, current-date question covering missing qualitative inputs. At minimum ask: “For `YYYY-MM-DD`, is there any pain or soreness this morning?” Also ask about illness symptoms, unusual fatigue, sleep disruption, or other context only when not already supplied and material to the decision.
8. Wait for the answer before interpreting readiness or writing durable files. Skip the wait only for an explicitly requested data-only extraction or when the user already supplied the needed context.

GarminDB may not contain training readiness or every wearable field. Mark those values unavailable unless another supplied source supports them.

## Workflow

1. Identify the current metric date and prior date.
2. Merge the newly synced GarminDB evidence into the existing prior-date database row first. Confirm prior sleep and add prior-day Body Battery/stress without moving either into the current-date entry.
3. Merge the current morning's user-supplied text or image into the current-date record. Preserve source provenance, uncertainty, approximate values, and missing fields; never let a lower-quality source silently overwrite a better one.
4. Write each completed date through the shared manager. Pass one JSON object using the established recovery-entry shape directly on standard input, then run:

   ```bash
   python3 .agents/scripts/manage_running_data.py --project-root . \
     upsert-recovery
   ```

   The command reads stdin by default, merges the date in `docs/running_data.db`, preserves full source detail in `details_json`, records repeatable qualitative observations separately, and regenerates `docs/recovery_metrics.md`. When the execution tool separates process launch from stdin, start the command and send the JSON object to that process. Do not create a temporary JSON file for the normal daily workflow. `--input PATH` remains available when a durable or inspectable payload is specifically useful.
5. Confirm the regenerated Markdown keeps newest entries first and no more than 14 daily rows. Query `history --kind recovery` for older dates rather than expanding the file.
6. Use only the most recent 7 valid daily entries for the immediate decision unless the user asks for a longer review.
7. Change the normalized plan and append a dated plan adjustment before regenerating `docs/running_plan.md` only if the new evidence materially changes the remaining week, next session, mileage cap, long run, quality session, or symptom handling. Use `upsert-plan`, `record-plan-adjustment`, or `set-plan-section`; do not edit historical prose directly into the Markdown file.
8. Version the affected profile section or add a profile measurement before regenerating `docs/runner_profile.md` only when a repeated or longer-term pattern materially changes the athlete model or risk assessment. Use `set-profile-section` or `record-profile-measurement`.

## Interpretation

- Separate the raw nightly value, rolling average, personal baseline range, and device status label.
- Treat baselines as dynamic. A status color can change because the baseline moved.
- Never clear, cancel, or restrict training from HRV status alone.
- Combine raw trends with sleep, resting HR, symptoms, illness, nutrition, perceived fatigue, recent load, and actual run response.
- Treat a single poor night with otherwise normal evidence differently from a multi-day negative cluster.
- Treat mild transient discomfort as a monitoring signal when it remains stable, does not alter mechanics, resolves within hours, and is absent the next morning.
- Escalate concern with recurrence in the same location, increasing severity or duration, morning stiffness, swelling, focal bone/tendon pain, altered gait, or worsening during activity.
- Avoid both errors: ignoring progressive symptoms and allowing minor transient symptoms to create chronic undertraining.

## Training Decision

Identify the session scheduled for the current date in `This Week's Plan`, then state the recommended session after accounting for the full recovery cluster and recent training load. Distinguish these explicitly when they differ.

Always give a concrete recommendation after the qualitative gate:

- If running is supported, name the run type and prescribe distance or duration, effort target using the most reliable combination of HR, and pace.
- If the planned run should be shortened or changed, state the original session, the replacement, why it changed, and when the original training intent can be reconsidered. (can be left blank)
- If rest is recommended or scheduled, say `No run today`, give any appropriate low-cost recovery activity, and state the next reassessment point.
- If the current plan has no dated session or is stale, say so. Give a conservative provisional recommendation only when the athlete profile, recent load, symptoms, and recovery evidence support it; otherwise state exactly what information is needed before prescribing a run.

Do not force an awkward shuffle, walking, or reduced mileage solely to satisfy an approximate wrist-HR number when breathing, RPE, mechanics, conditions, and the broader trend show controlled effort.

## Response

Report:

- what was recorded and any missing or conflicting fields;
- the meaningful recovery signals, not every device value;
- the scheduled session and the specific recommended run or rest prescription for today;
- the reason for any change, relevant execution/stop conditions, and reassessment point;
- which database records and compact private projections were updated and why.
