# GarminDB Bootstrap Analysis

Follow this reference only after the initial GarminDB import has completed and its databases have passed targeted verification. Its purpose is to turn the private raw import into a compact coaching baseline before asking the athlete questions that the data can answer.

## 1. Establish Actual Coverage

Resolve and state the exact imported coverage before interpreting anything:

- inspect the live schema of each GarminDB SQLite database before querying it;
- count running activities and identify their earliest and latest local dates in `garmin_activities.db`;
- confirm lap, record, split, GPS-record, HR, cadence, power, and device coverage separately where those streams matter;
- identify the earliest and latest available dates independently for sleep, resting HR, HRV, daily summary, monitoring, and derived summaries;
- distinguish the requested daily-data start date from actual per-stream coverage;
- distinguish the activity download cap from complete activity-history coverage—a count-limited download does not prove that older history is complete.

Use read-only SQLite connections and date-bounded or aggregate queries. Never select, print, summarize, or persist route coordinates. Do not read or display credentials or tokens.

## 2. Analyze the Objective History Before Asking Questions

Analyze all imported running activities at aggregate level, with recent 4-, 8-, and 12-week views where coverage allows. Establish:

- runs per week and month, weekly distance and duration, consistency, gaps, and recent direction of volume;
- longest run overall, longest recent run, long-run frequency, and long-run share of weekly volume;
- pace distributions and changes only across reasonably comparable runs;
- average and maximum HR distributions, HR-data coverage, device changes, and obvious sensor artifacts;
- cadence, power, training load/effect, ascent/descent, and sub-sport patterns only where coverage is adequate;
- recorded activity mix, including walking, cycling, strength, or other cross-training when present;
- possible race, time-trial, workout, or benchmark candidates, labeled as candidates until context confirms their purpose;
- recent workload relative to the athlete's demonstrated historical range, without assuming that historical tolerance guarantees current readiness.

Analyze recovery data by exact date and stream. Establish recent sleep duration/score, resting HR, HRV, Body Battery, and stress patterns over the most recent 28 valid days, extending toward 90 days only when it materially improves the baseline or trend interpretation. Mark training readiness and other unsupported wearable fields unavailable rather than inferring them.

Prefer aggregate queries for the full history. Use original FIT files selectively when record-level detail would materially improve the baseline—for example, a recent representative easy run, the longest recent run, a benchmark candidate, or a suspected sensor artifact. Do not parse every FIT file merely because it exists.

## 3. Persist a Selective Coaching Projection

Keep GarminDB as the complete raw upstream source. Do not copy its raw tables into `docs/running_data.db`.

Use the shared manager and its established contracts to persist only coaching-ready evidence:

- `recovery_daily`: import the most recent 28 valid daily records by default, with exact source provenance and missing fields preserved; extend up to 90 days only when needed to support a material trend or baseline;
- `training_summaries`: store each complete recent week needed for the initial plan, normally the latest 12 weeks, and use monthly summaries for older imported history when it adds useful development context;
- `profile_entries`: store compact conclusions about consistency, frequency, sustainable volume, long-run history, pace/HR/cadence patterns, activity mix, device/sensor coverage, and current recovery baseline, including the supporting date range and material limitations;
- `profile_measurements`: store only measurements with clear dates, canonical units, and source provenance.

Do not bulk-create `activity_reviews`. An activity belongs there only after the `analyze-running-activity` workflow has resolved it, collected needed qualitative context, and produced an actual coaching interpretation. Do not persist raw GPS records, routes, laps, splits, monitoring samples, or Garmin credentials/tokens in the coaching database.

Make writes idempotent through the manager's existing date, period, and entry keys. Run the database verifier and regenerate the affected Markdown projections after the multi-record bootstrap.

## 4. Prepare the Qualitative Gap List

Before asking the athlete anything, produce a compact internal evidence ledger with:

- facts directly supported by GarminDB;
- estimates that depend on coverage or comparability assumptions;
- unavailable or unreliable objective fields;
- qualitative unknowns that could change the initial athlete model or plan.

Do not ask for a fact already supported by the imported data. Ask for correction only when a material ambiguity exists, such as mixed units, incomplete history, a likely non-running activity classification, unreliable HR, or an apparent benchmark whose purpose is unknown.

Return control to the main initialization workflow only after coverage, aggregate analysis, selective persistence, and the qualitative gap list are complete.
