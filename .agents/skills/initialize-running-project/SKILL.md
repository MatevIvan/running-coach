---
name: initialize-running-project
description: Initialize a fresh clone of the privacy-first running-coach repository by creating its ignored private workspace, collecting athlete onboarding information, seeding the live runner profile and running plan, explaining recommended chat workflows, and optionally installing, configuring, and running GarminDB. Use when a user asks to initialize, onboard, set up, bootstrap, or connect Garmin data for a new copy of this project.
---

# Initialize Running Project

## Goal

Create a usable private athlete workspace and its SQLite record without exposing personal data or credentials, then leave the user with a clear workflow for ongoing coaching, recovery collection, and activity analysis.

Read `.agents/running_data/CONTRACT.md` before seeding athlete, event, or plan records.

## Required Order

Treat initialization as a gated conversation, not one uninterrupted command sequence.

### 1. Ask About GarminDB First

Make the first user-facing question:

> Would you like to connect GarminDB during setup? You can answer yes, no, or not now.

Wait for the answer before creating or installing anything. Do not combine this with the athlete questionnaire.

- For **yes**, record the decision and continue through core setup before the GarminDB branch.
- For **no** or **not now**, skip all GarminDB installation and credential steps. Explain that it can be added later by invoking this skill again.

### 2. Protect the Privacy Boundary

Before writing athlete data:

1. Locate the project root containing `AGENTS.md`.
2. Inspect existing paths without reading example values as athlete data.
3. Confirm Git ignores `docs/` with `git check-ignore docs/.privacy-check`.
4. Confirm `.venv/` is ignored when GarminDB was selected.
5. Add missing ignore rules before creating private content.
6. Never force-add `docs/`, credentials, tokens, databases, logs, FIT/GPX files, or generated reports.

Stop if `docs/` cannot be kept outside Git.

### 3. Create the Private Workspace

Run:

```bash
python3 .agents/skills/initialize-running-project/scripts/initialize_private_workspace.py --project-root .
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

### 4. Onboard the Athlete in Short Batches

Ask only questions that materially improve the initial athlete model. Accept “unknown,” “not applicable,” and “prefer not to answer.” Do not request all answers in one oversized message.

First collect the minimum baseline:

- primary running goals and what meaningful growth would look like over the next few months;
- any confirmed or likely race/event, including date, distance, course context, and finish-versus-performance priority; explicitly record `none` when no event is planned;
- recent weekly running volume and frequency;
- longest recent run and any useful recent race, time trial, workout, or benchmark;
- running history and current consistency;
- current pain, recurring symptoms, major prior running injuries, or relevant clinician-imposed limits;
- preferred units and timezone.

Store each completed current-profile section with `manage_running_data.py set-profile-section`; the command versions the database entry and regenerates `docs/runner_profile.md`. Distinguish facts supplied by the user, estimates, and unknowns. Do not append historical ledgers to the Markdown file.

Then collect operating constraints:

- available and preferred run days, long-run day, and time constraints;
- typical terrain, climate, surfaces, and elevation;
- usual easy effort or pace and any trustworthy HR/threshold information;
- strength training and cross-training;
- watch, HR strap, foot pod, power meter, and available Garmin/Strava history;
- fueling experience and equipment constraints relevant to the goal.

Update the profile again through the database command. Create a provisional plan with `manage_running_data.py upsert-plan`, then store its compact current sections with `set-plan-section`; those commands regenerate `docs/running_plan.md`. Do not require a race date: without an event, create a 4-12 week development block with a named objective and review date; with a confirmed event, add the appropriate event-specific horizon. Mark unresolved items explicitly; do not invent zones, mileage history, benchmark evidence, or races.

If substantial historical data will be imported, keep the first plan conservative and provisional until that data has been reviewed.

### 5. Complete the GarminDB Branch Only When Selected

Read [references/garmindb-setup.md](references/garmindb-setup.md) completely, then follow it in order.

Do not ask the user to paste a Garmin password, MFA code, token, or configuration contents into chat. Generate the private configuration, show its path, and pause while the user edits credentials locally.

### 6. Explain the Recommended Chat Structure

Give the user a compact orientation after setup:

- **Coach chat:** General coaching, weekly reviews, development blocks, plan changes, missed sessions, symptoms affecting future training, race preparation when applicable, and “what should I do next?” Use `coach-runner`.
- **Run-analysis chat:** Review a completed run from a FIT/GPX file, screenshot, or written metrics. Include purpose, RPE, pain/soreness, terrain/surface, and fueling. When GPS data is available, the skill derives a privacy-limited location and retrieves historical weather automatically. Use `analyze-running-activity`.
- **Daily-metrics chat:** Manually provide the current morning's sleep and wearable metrics plus fatigue, illness, soreness, and pain. When GarminDB is connected, `collect-daily-metrics` automatically syncs through the prior day, confirms the prior day's sleep, and adds its finalized Body Battery/stress data before interpreting the current morning. This is optional when no daily decision is needed, but useful during heavy training, poor recovery, or symptom monitoring.
- **Setup/data chat:** Maintain GarminDB, `docs/running_data.db`, imports, privacy checks, and integration failures. Reuse the initialization chat or create a dedicated maintenance chat.
- **Gear-research chat:** Use `research-running-gear` for purchases that need current product research.

Explain that separate chats improve focus. `docs/running_data.db` preserves durable history, while the three Markdown projections provide compact current context. New chats must use live private data and never the root examples.

## Completion Check

Before declaring setup complete:

- confirm the private files and `docs/running_data.db` exist, then run the database verifier;
- confirm `git status --short` does not show anything under `docs/`;
- summarize which onboarding fields remain unknown;
- identify whether the initial plan is absent, provisional, or active;
- report whether GarminDB was skipped, deferred, configured, or successfully imported;
- when GarminDB ran, report the installed version, requested data horizon, database location, and any targeted import errors;
- give the exact next chat the user should start.

Do not treat an incomplete credential step, MFA challenge, failed import, or missing private file as successful initialization.
