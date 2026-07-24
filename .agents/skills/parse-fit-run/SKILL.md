---
name: parse-fit-run
description: Parse Garmin/Strava running .fit files for coaching analysis. Use when Codex needs to inspect a FIT activity file, extract run metrics, validate activity date/time, compute distance/time/pace/heart-rate/cadence/power summaries, build splits, compare first half vs second half, or prepare objective data for a run review.
---

# Parse FIT Run

## Overview

Extract an objective activity record from a running FIT file. This is a low-level parsing skill; use `analyze-running-activity` for coaching interpretation, plan changes, and durable file updates.

## Quick Start

Run:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py path/to/activity.fit
```

For machine-readable output:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py path/to/activity.fit --json
```

If the current working directory is not the project root, use the absolute path to the script.

## Parsing Workflow

1. When no FIT path is supplied but an activity date or ID is known, check `docs/garmindb/data/DBs/garmin_activities.db` for the matching activity and look for its downloaded FIT under `docs/garmindb/data/FitFiles/Activities/`. Do not silently select among multiple matches.
2. Parse the FIT file with `scripts/parse_fit_run.py`.
3. Use local start date/time from the parser when confirming run date.
4. Use record-derived distance, duration, pace, average HR, max HR, cadence, power, HR-zone distribution, splits, and first-half/second-half comparison.
5. Treat `session` and `lap` values as supporting data. If a session field is missing or suspicious, rely on record-derived values.
6. Report missing streams, implausible values, and likely GPS, HR, cadence, or pause artifacts.
7. Return the parsed record to the calling workflow. Do not update the runner profile or marathon plan from this parser alone.

The calling analysis skill owns the dated qualitative-question gate. This low-level parser returns objective data only and must not infer pain, effort, weather, session purpose, or physiological meaning.

## Parser Notes

- The script is dependency-free and implements the subset of FIT decoding needed for running activity review.
- It decodes FIT definition messages and data messages, then extracts global message types `record`, `lap`, `session`, and `activity`.
- It applies common FIT scale factors for distance, speed, altitude, and timestamps.
- It uses the default project HR zones from the runner profile unless custom zone cutoffs are passed.
- It reports cadence both as FIT single-foot cadence and approximate steps per minute.

## Cautions

- Prefer record-derived metrics over screenshots or activity labels when they conflict.
- Flag impossible GPS, HR, cadence, power, or pace values rather than silently accepting them.
- Do not infer weather, terrain, symptoms, session purpose, or physiological meaning from the FIT file alone.
