---
name: initialize-running-project
description: Initialize a fresh clone of the privacy-first running-coach repository by creating its ignored private workspace, prioritizing GarminDB installation and import when selected, deriving the objective athlete baseline before qualitative onboarding, and seeding the live runner profile and running plan. Use when a user asks to initialize, onboard, set up, bootstrap, connect Garmin data, or build a coaching baseline for a new copy of this project.
---

# Initialize Running Project

## Goal

Create a usable private athlete workspace and SQLite record without exposing personal data or credentials. When GarminDB is selected, get it running and process its objective history before asking coaching questions, then collect only the qualitative context and constraints that the imported data cannot establish.

Read `.agents/running_data/CONTRACT.md` before seeding athlete, event, or plan records.

Detect the host operating system before running commands. Use `python3` on macOS/Linux and an available `py -3` or `python` launcher on Windows. Invoke Python scripts through the interpreter; do not rely on Unix shebang execution or copy POSIX line continuations into PowerShell.

## Required Order

Treat initialization as a gated conversation, not one uninterrupted command sequence.

### 1. Ask About GarminDB First

Make the first user-facing question:

> Would you like to connect GarminDB during setup? You can answer yes, no, or not now.

Wait for the answer before creating or installing anything. Do not combine this with the athlete questionnaire.

- For **yes**, record the decision, create the protected private workspace, and complete the GarminDB import and objective-data review before athlete onboarding.
- For **no** or **not now**, skip all GarminDB installation and credential steps. Explain that it can be added later by invoking this skill again.

### 2. Protect the Privacy Boundary

Before writing athlete data:

1. Locate the project root containing `AGENTS.md`.
2. Inspect existing paths without reading example values as athlete data.
3. Confirm Git ignores `docs/` with `git check-ignore docs/.privacy-check`.
4. Confirm `.venv/` is ignored when GarminDB was selected.
5. Add missing ignore rules before creating private content.
6. Never force-add `docs/`, credentials, tokens, databases, logs, FIT/GPX files, or generated reports.
7. On Windows, confirm the repository is in a private user-owned location. Explain that the scripts request restrictive POSIX modes where supported but do not replace inherited Windows ACLs; ask the user to review the `docs/` ACL when the machine or workspace is shared.

Stop if `docs/` cannot be kept outside Git.

### 3. Create the Private Workspace

Run:

```bash
python3 .agents/skills/initialize-running-project/scripts/initialize_private_workspace.py --project-root .
```

Windows PowerShell equivalent:

```powershell
py -3 .agents\skills\initialize-running-project\scripts\initialize_private_workspace.py --project-root .
```

Add `--with-garmindb` only when GarminDB was selected.

The script copies blank structural templates from `assets/private-workspace/`, applies the versioned SQLite migrations, creates supporting directories, and preserves every existing file. Never replace an existing athlete profile, plan, Garmin configuration, token, or database during initialization.

Verify that these live paths exist:

- `docs/runner_profile.md`
- `docs/running_plan.md`
- `docs/recovery_metrics.md`
- `docs/running_data.db`
- `docs/activities/`
- `docs/imports/`
- `docs/screenshots/`
- `docs/athlete_reports/`

Run the database verifier and do not copy mock values from root example files:

```bash
python3 .agents/scripts/manage_running_data.py --project-root . verify
```

Windows PowerShell equivalent:

```powershell
py -3 .agents\scripts\manage_running_data.py --project-root . verify
```

### 4. Complete GarminDB Before Coaching Onboarding When Selected

When GarminDB was selected, read [references/garmindb-setup.md](references/garmindb-setup.md) completely and follow it in order now. Before the import, ask only for GarminDB setup choices: history horizon, activity cap, units, weight-data preference, and credential mode. Do not mix in the athlete questionnaire.

Do not ask the user to paste a Garmin password, MFA code, token, or configuration contents into the conversation. Generate the private configuration, show its path, and pause while the user edits credentials locally. Stay with the initial import until it succeeds, fails with a precise cause, or requires a user MFA/Keychain action. Do not start duplicate imports.

If the GarminDB install or import cannot complete, preserve the private workspace and report the exact failed stage. Ask whether the user wants to retry, defer GarminDB and continue with manual onboarding, or stop. Never describe an incomplete import as a usable objective baseline.

### 5. Process the Imported GarminDB History

After a verified GarminDB import, read [references/garmindb-bootstrap-analysis.md](references/garmindb-bootstrap-analysis.md) completely and follow it before asking coaching questions or creating a plan.

Take enough time to inspect coverage and process the full imported activity history plus the recovery window relevant to current coaching. Derive supported facts about running frequency, weekly volume and duration, consistency, longest runs, pace and HR patterns, cadence, elevation, activity mix, devices/sensors, and recent recovery. Separate supported facts, estimates, and unavailable fields. Do not infer pain, intent, perceived effort, schedule constraints, or goals from device data.

Persist only the coaching-ready projection described in the bootstrap reference. Keep GarminDB as the complete raw upstream source; do not mirror raw route points, records, laps, or every unreviewed activity into `docs/running_data.db`.

### 6. Collect Only the Remaining Qualitative Baseline

Ask only questions whose answers remain unknown and would materially improve the athlete model or initial plan. Accept “unknown,” “not applicable,” and “prefer not to answer.” Keep each batch short.

For a successful GarminDB import, do not ask the user to restate objective facts already supported by the data, including recent weekly volume or frequency, longest recorded run, recorded pace/HR/cadence patterns, device history, or available activity dates. Instead, summarize what the data appears to show and ask only for correction when a material ambiguity remains.

Normally collect:

- primary running goals and what meaningful growth would look like over the next few months;
- any confirmed or likely event, including date, distance, course context, and finish-versus-performance priority; explicitly record `none` when no event is planned;
- current pain, recurring symptoms, major prior running injuries, and relevant clinician-imposed limits;
- available and preferred run days, long-run day, time constraints, and timezone;
- typical surface or terrain only when it cannot be established without exposing or reverse-geocoding private routes;
- strength training, unrecorded cross-training, fueling experience, and equipment constraints not present in the data;
- perceived easy effort, breathing, and subjective recovery only when those details would change interpretation.

When GarminDB was skipped or deferred, also collect the objective baseline manually: recent weekly volume and frequency, longest recent run, running history and consistency, useful races/time trials/workouts, usual easy effort or pace, trustworthy HR/threshold information, and device history.

Store complete current-profile sections with `manage_running_data.py set-profile-section`; the command versions the database entry and regenerates `docs/runner_profile.md`. Distinguish data-supported facts, user reports, estimates, and unknowns. Do not append historical ledgers to Markdown.

### 7. Create the Initial Plan After the Baseline Is Complete

Create a provisional plan only after the imported objective evidence and qualitative answers have both been processed. Use `manage_running_data.py upsert-plan`, then store compact current sections with `set-plan-section`; those commands regenerate `docs/running_plan.md`.

Do not require a race date. Without an event, create a 4-12 week development block with a named objective and review date; with a confirmed event, add the appropriate event-specific horizon. Mark unresolved items explicitly and do not invent zones, mileage history, benchmark evidence, or races. Keep the first plan conservative and provisional when GarminDB coverage is partial or material qualitative answers remain unknown.

### 8. Explain the Recommended Conversation Structure

Give the user a compact orientation after setup:

- **Coach conversation:** General coaching, weekly reviews, development blocks, plan changes, missed sessions, symptoms affecting future training, race preparation when applicable, and “what should I do next?” Use `coach-runner`.
- **Run-analysis conversation:** Review a completed run from a FIT/GPX file, screenshot, or written metrics. Include purpose, RPE, pain/soreness, terrain/surface, and fueling. When GPS data is available, the skill derives a privacy-limited location and retrieves historical weather automatically. Use `analyze-running-activity`.
- **Daily-metrics conversation:** Manually provide the current morning's sleep and wearable metrics plus fatigue, illness, soreness, and pain. When GarminDB is connected, `collect-daily-metrics` automatically syncs through the prior day, confirms the prior day's sleep, and adds its finalized Body Battery/stress data before interpreting the current morning. This is optional when no daily decision is needed, but useful during heavy training, poor recovery, or symptom monitoring.
- **Setup/data conversation:** Maintain GarminDB, `docs/running_data.db`, imports, privacy checks, and integration failures. Reuse the initialization conversation or create a dedicated maintenance conversation.
- **Gear-research conversation:** Use `research-running-gear` for purchases that need current product research.

Explain that separate conversations improve focus. `docs/running_data.db` preserves durable history, while the three Markdown projections provide compact current context. New conversations must use live private data and never the root examples.

## Completion Check

Before declaring setup complete:

- confirm the private files and `docs/running_data.db` exist, then run the database verifier;
- confirm `git status --short` does not show anything under `docs/`;
- summarize which onboarding fields remain unknown;
- identify whether the initial plan is absent, provisional, or active;
- report whether GarminDB was skipped, deferred, configured, or successfully imported;
- when GarminDB ran, report the installed version, requested and actual coverage, database location, and any targeted import errors;
- when GarminDB was processed, report the activity and recovery ranges reviewed, important coverage gaps, which recovery dates and training-summary periods were projected into `docs/running_data.db`, and which profile sections were derived from that evidence;
- give the exact next conversation the user should start.

Do not treat an incomplete credential step, MFA challenge, failed import, unprocessed GarminDB history, unanswered material qualitative question, or missing private file as successful initialization.
