---
name: collect-daily-metrics
description: Collect, validate, store, and interpret daily GarminDB, Garmin, or self-reported recovery metrics. Use when the user provides or requests sleep duration or score, resting heart rate, HRV value/status/baseline, training readiness, Body Battery, stress, soreness, pain, illness, fatigue, nutrition, or daily recovery screenshots; asks whether to train today; or requests an update to the private recovery log.
---

# Collect Daily Metrics

## Goal

Turn daily recovery information into an accurate permanent record, a compact rolling view, and a proportionate training implication without overreacting to one metric.

## Read First

Read:

- `docs/recovery_metrics_raw.json`
- `docs/recovery_metrics.md`
- `docs/marathon_plan.md`
- `docs/runner_profile.md` only when baseline, symptoms, or a durable trend matters

Never use root example files as live data.

## GarminDB and Qualitative Gate

Complete this sequence before interpreting recovery or updating files:

1. Resolve and state the morning metric date as `YYYY-MM-DD`. Keep prior-day Body Battery, stress, activity, or nutrition context attached to its actual date.
2. Check for `docs/garmindb/data/DBs/garmin.db` and, when needed, `garmin_monitoring.db` and `garmin_summary.db`.
3. Query the target date read-only:

   ```bash
   python3 .agents/skills/collect-daily-metrics/scripts/read_garmindb_daily.py \
     --project-root . --date YYYY-MM-DD
   ```

   For a trend review, use `--start-date YYYY-MM-DD --end-date YYYY-MM-DD`. Check each source independently, including `sleep`, `resting_hr`, `hrv`, `daily_summary`, and relevant monitoring or summary rows. Do not assume one present row means the day is complete.
4. Extract available objective values with source and date provenance. Do not ask the user to transcribe metrics already present in GarminDB.
5. If the date is absent or the database is stale, say which metrics are unavailable and offer an incremental GarminDB sync before requesting manual values.
6. After objective extraction, ask one concise, dated question covering missing qualitative inputs. At minimum ask: “For `YYYY-MM-DD`, is there any pain or soreness this morning?” Also ask about illness symptoms, unusual fatigue, sleep disruption, or other context only when not already supplied and material to the decision.
7. Wait for the answer before interpreting readiness or writing durable files. Skip the wait only for an explicitly requested data-only extraction or when the user already supplied the needed qualitative context.

GarminDB may not contain training readiness or every wearable field. Mark those values unavailable unless another supplied source supports them.

## Workflow

1. Identify the metric date. Distinguish the morning measurement date from the prior day's Body Battery, stress, or activity context.
2. Merge values supported by GarminDB with the user's text or image. Preserve source provenance, uncertainty, approximate values, and missing fields; never let a lower-quality source silently overwrite a better one.
3. Check the existing raw entry for that date.
4. Update `docs/recovery_metrics_raw.json` first:
   - merge a resubmitted date instead of duplicating it;
   - preserve valid fields not replaced by newer evidence;
   - keep all older entries;
   - retain raw device wording where it helps provenance.
5. Update `docs/recovery_metrics.md` second:
   - keep newest entries first;
   - keep no more than 14 daily rows;
   - summarize the day's recovery cluster and training implication compactly.
6. Use only the most recent 7 valid daily entries for the immediate decision unless the user asks for a longer review.
7. Update `docs/marathon_plan.md` only if the new recovery evidence materially changes the remaining week, next session, mileage cap, long run, or symptom handling.
8. Update `docs/runner_profile.md` only when a repeated or longer-term pattern materially changes the athlete model or risk assessment.

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

State whether the evidence supports the planned session, an easy modification, rest, or additional information. Give restrictions a specific reason and a clear reassessment point.

Do not force an awkward shuffle, walking, or reduced mileage solely to satisfy an approximate wrist-HR number when breathing, RPE, mechanics, conditions, and the broader trend show controlled effort.

## Response

Report:

- what was recorded and any missing or conflicting fields;
- the meaningful recovery signals, not every device value;
- the implication for today's or the next planned session;
- which private files were updated and why.
