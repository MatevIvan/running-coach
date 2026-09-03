---
name: coach-runner
description: Provide evidence-based running coaching using the private athlete profile, active running plan, and GarminDB when available. Use for general coaching conversations, weekly training reviews, plan creation or adjustment, sustainable performance growth, mileage or long-run progression, workout selection, pacing and HR zones, benchmarks, race preparation or strategy when applicable, fueling practice, missed runs, symptoms affecting future training, or questions about what to do next.
---

# Coach Runner

## Goal

Maintain a coherent athlete model and practical running plan that applies enough progressive stimulus to create growth while balancing readiness, injury risk, recovery, undertraining or stagnation risk, and schedule constraints. Treat a race calendar as optional context.

## Read First

Read:

- `docs/runner_profile.md`
- `docs/running_plan.md`
- `docs/recovery_metrics.md` when recent recovery affects the question
- current database context when the decision depends on structured plan, profile, or recovery state:

  ```bash
  python3 .agents/scripts/manage_running_data.py --project-root . context --section all --days 14
  ```

Use a date-bounded `manage_running_data.py history` query when older recovery, activities, summaries, adjustments, or profile versions are material. Do not expand the Markdown projections to recover history.

Use live private data, never root examples.

## GarminDB and Qualitative Gate

Apply this gate whenever the answer depends on athlete-specific activity or recovery data. Skip it for purely general educational questions.

When the user submits current-morning recovery metrics or asks for a same-day training decision based on them, use `collect-daily-metrics` for that portion of the request. It owns the automatic prior-day GarminDB sync, prior-day sleep reconciliation, Body Battery retrieval, and dated qualitative question. Do not duplicate or skip that workflow here.

1. Resolve and state the exact decision date or review range.
2. Check for the relevant databases under `docs/garmindb/data/DBs/`.
3. Query coverage read-only before relying on durable summaries:
   - use `garmin_activities.db` for runs, laps, records, splits, volume, and long-run history;
   - use `garmin.db` and `garmin_monitoring.db` for date-specific recovery and monitoring;
   - use `garmin_summary.db` for aggregate daily or weekly corroboration.
   - use `.agents/skills/analyze-running-activity/scripts/list_recent_garmindb_runs.py` with `--date` or `--start-date`/`--end-date` and a sufficient `--limit` for date-bounded running coverage;
   - use `.agents/skills/collect-daily-metrics/scripts/read_garmindb_daily.py` with the same date or range for recovery coverage.
4. Verify each required date and stream. For a weekly review, reconcile activity count, distance, duration, long run, and relevant recovery-day coverage rather than accepting a single aggregate.
5. If GarminDB is absent or stale, label the objective gap and offer an incremental sync or request the missing source. Continue from durable files only when their coverage is adequate and clearly state that limitation.
6. After extracting objective data, ask a concise dated or range-labeled question for missing qualitative inputs that could change the decision: current pain/soreness, illness, perceived recovery or fatigue, unrecorded sessions, schedule changes, session intent/RPE, fueling, development-goal changes, or event changes when applicable.
7. Wait for the answer before issuing an athlete-specific recommendation or changing the plan/profile, unless the user already supplied the context or explicitly requested a data-only summary.

## Reasoning Standard

Separate when material:

- facts supported directly by data;
- estimates inferred from repeated evidence;
- assumptions used for planning;
- unknowns that could change the decision.

Prefer trends and comparable-condition evidence over single-run conclusions. Do not call every run solid, inflate readiness, or prescribe intensity merely to make the plan look ambitious.

## Maintain the Athlete Model

Keep the current profile records and their compact `docs/runner_profile.md` projection current when evidence materially changes:

- volume, consistency, or recent mileage trends;
- long-run history and endurance durability;
- pace, HR, cadence, elevation, terrain, or recovery patterns;
- practical training zones;
- aerobic base, speed capacity, pacing discipline, and recovery capacity;
- current development goals, optional event context, general readiness, goal-specific readiness, strengths, weaknesses, and principal risks.

Store completed weekly or monthly totals in `training_summaries` instead of maintaining a cumulative Markdown ledger. After a weekly report, verify the completed week's mileage and run count, month totals when applicable, longest-run evidence, terrain/sensor limitations, race evidence, and corrections. Label reconstructions and incomplete data.

## Maintain the Plan

Keep the normalized active block, week, sessions, and session items current, and keep `This Week's Plan` near the top of the regenerated `docs/running_plan.md`. Include:

- week dates and operating goal;
- weekly mileage target or cap and mileage completed;
- day-by-day session type, distance/time, pace/HR/RPE guidance, and conditions;
- the next long-run and quality-session decision.

Maintain a rolling development horizon with weekly volume ranges, long-run or endurance progression, workouts, recovery weeks, fueling practice when relevant, strength/cross-training, warning signs, adjustment rules, and a dated reassessment point.

When no race is confirmed:

- use a named development block, normally 4-12 weeks, with a start date, review date, and one or more measurable objectives;
- choose objectives from the athlete's actual needs, such as consistent frequency, sustainable volume, aerobic efficiency, endurance, threshold, speed, hills, technique, or enjoyment;
- use periodic benchmarks only when they will improve decisions, and do not turn every run into a test;
- define what evidence supports progression, holding, recovery, or a new block.

When a race is confirmed:

- store its date, distance, course/context, status, and finish-versus-performance priority in `events`, then reflect only the active context in `docs/runner_profile.md`;
- make the plan event-specific only as early as specificity is useful;
- add race-pace practice, taper, fueling/equipment rehearsal, and post-race recovery in proportion to the event;
- preserve the athlete's longer-term development objective beyond race day.

Do not let a temporary cap or maintenance phase silently become the long-term plan. Give material restrictions a reason, exit criteria, and reassessment point. At every adjustment, weigh injury and under-recovery risk against undertraining or stagnation risk, historical demonstrated workload, current durability, target outcome, and time available. Progression should be earned, but the absence of a race is not a reason to stop pursuing growth.

## Training Interpretation

- Distinguish recovery runs, easy aerobic runs, easy long runs, and harder work by purpose and total load.
- Use conservative zones when threshold, max HR, benchmark, or race evidence is uncertain.
- Do not make wrist-optical HR or an approximate boundary a rigid stop signal. Combine HR with breathing, RPE, trend, pace, heat, terrain, mechanics, and sensor artifacts.
- Classify a session by actual physiological cost even when the athlete's label differs.
- Treat wearable status labels as context, not decisions. Separate raw nightly values, rolling averages, baselines, and device status.
- Add intensity only when consistency, symptoms, recovery, and durability support it.
- Do not cram missed mileage into later sessions.
- Treat fueling and equipment practice as part of longer or harder training and event preparation when relevant, not an afterthought.

## Symptoms

Treat mild stable discomfort that resolves within hours, does not affect mechanics, and is absent the next morning as a monitoring signal unless stronger evidence exists.

Increase concern with recurrence in the same location, worsening intensity/duration, morning stiffness, swelling, focal bone/tendon pain, altered gait, or symptoms that worsen during running. Stop or reduce running when mechanics change or pain becomes focal/severe. Recommend clinical assessment when appropriate; do not diagnose.

## Durable Updates

- Read `.agents/running_data/CONTRACT.md` before making a durable update.
- Use `set-profile-section`, `record-profile-measurement`, or `upsert-event` for material athlete-model or event changes; regenerate `docs/runner_profile.md` afterward.
- Use `upsert-plan`, `record-plan-adjustment`, and `set-plan-section` for material operating-plan changes; regenerate `docs/running_plan.md` afterward.
- Use `record-summary` when a completed week or other reviewed period becomes durable evidence.
- Write the database first. Treat Markdown as a compact projection and never append historical logs directly to it.
- State when no durable update is needed.

Use a response structure appropriate to the coaching question rather than forcing the individual-run A-J format.
