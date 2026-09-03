# Privacy-First Running Coach

This repository turns Codex into a persistent running-performance analyst and coach. It combines Garmin/Strava activity data, recovery metrics, a living runner profile, and an adaptive running plan while keeping the athlete's personal data outside Git.

The project is designed to track runs, explain what the training is doing, and plan progressive work that helps the runner improve in a healthy, sustainable way. A race can shape the plan when one is scheduled, but no race is required: without one, the coach uses development blocks, measurable objectives, and dated reassessments. It is not medical software and does not diagnose health conditions.

## Privacy Model

All real athlete data lives in `docs/`, which is ignored by Git. This includes:

- The private SQLite history and compact runner-profile, running-plan, and recovery projections
- FIT, GPX, CSV, screenshot, and export data
- Generated athlete reports and any other derived personal documents

Only reusable instructions, tooling, and synthetic examples belong in the public repository. Never force-add `docs/` or copy personal values into an example file.

Important: `.gitignore` prevents untracked files from being added normally, but it cannot remove data that was already committed. Run a Git status check before every public push, and treat any previously committed personal data as a history-cleanup incident.

## Repository Layout

```text
.
├── AGENTS.md                         # Project context, privacy, and skill routing
├── README.md                         # Project overview and setup
├── .gitignore                        # Excludes all private athlete data
├── docs/                             # Private local workspace; never committed
│   ├── runner_profile.md             # Living athlete model
│   ├── running_plan.md               # Active plan, current week, and development horizon
│   ├── running_data.db                # Durable recovery, profile, activity, and plan history
│   ├── recovery_metrics.md           # Rolling 14-day recovery view
│   ├── activities/                   # New FIT/GPX activities
│   └── ...                           # Exports, reports, screenshots, and notes
├── .agents/
│   └── skills/
│       ├── initialize-running-project/ # Fresh-clone onboarding and optional GarminDB
│       ├── collect-daily-metrics/    # Daily recovery collection and decisions
│       ├── analyze-running-activity/ # Completed-run review workflow
│       ├── coach-runner/             # Planning and coaching conversations
│       ├── research-running-gear/    # Current purchase research
│       └── parse-fit-run/            # Dependency-free FIT activity parser
├── runner_profile_example.md         # Synthetic structure example
├── running_plan_example.md           # Synthetic structure example
└── recovery_metrics_example.md       # Synthetic rolling-view example
```

The root example files are documentation only. `AGENTS.md` explicitly prohibits treating them as real athlete data.

## How Project Instructions Work

`AGENTS.md` is the project constitution. It gives every chat the shared privacy boundary, database and projection contracts, and common coaching standards. See the official [AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Each folder under `.agents/skills/` contains a specialized prompt in `SKILL.md`. Codex scans this repository location automatically. The skill description supports implicit selection: when a request matches it, Codex loads that skill's detailed workflow. `AGENTS.md` also contains a compact routing table so the intended relationship remains explicit and understandable. See the official [skills documentation](https://learn.chatgpt.com/docs/build-skills).

The current roles are:

- `initialize-running-project`: create the ignored private workspace, collect the initial athlete baseline, and optionally install and import GarminDB.
- `collect-daily-metrics`: record and interpret recovery data.
- `analyze-running-activity`: review a completed run and decide whether the plan or profile changes.
- `coach-runner`: answer coaching questions and maintain the broader plan and athlete model.
- `research-running-gear`: research current products against athlete-specific needs.
- `parse-fit-run`: parse FIT files for the activity-analysis workflow.

This keeps global context small and loads scenario-specific instructions only when needed.

## Planning Model

`docs/running_data.db` stores the durable athlete history. `docs/runner_profile.md` is a compact current projection containing the athlete's continuing development goals and an explicit `Goals and Event Context` section. That section records `none` when no event is planned; when a race is relevant, it records the date, distance, course context, and finish-versus-performance priority.

`docs/running_plan.md` is a compact projection that always has a current week, a broader development objective, and a dated reassessment point. Completed weeks and superseded adjustments remain queryable in SQLite rather than accumulating in Markdown. Without a race, it uses a 4-12 week development block with measurable progression criteria. With a confirmed race, it adds only the event-specific work, taper, rehearsal, and recovery that the event actually requires.

## Getting Started

1. Clone the repository.
2. Open the repository as a Codex project.
3. Ask Codex: `Use $initialize-running-project to set up this project for me.`
4. Choose whether to connect GarminDB, then complete the short athlete questionnaire.
5. If GarminDB is selected, edit credentials only in the generated private file when prompted; never paste them into chat.
6. Put any other Garmin/Strava exports and future FIT/GPX activities under `docs/`.

If the private database or current projections do not exist, Codex should report that live athlete data is unavailable. It should never fall back to the synthetic examples.

## FIT Activity Parsing

The bundled parser extracts record-derived distance, time, pace, HR, cadence, power, splits, HR-zone distribution, and first-half/second-half comparisons from a running FIT file.

Human-readable output:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py docs/activities/example.fit
```

Machine-readable output:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py docs/activities/example.fit --json
```

The parser uses only Python's standard library.

## Normal Workflow

For a new run:

1. Ask `analyze-running-activity` to review the run. When GarminDB is connected, it first performs an incremental activity sync; otherwise, add the activity file under `docs/activities/` or provide its details in chat.
2. Confirm the candidate activity identified by the skill.
3. Answer its short follow-up about information the device does not know, such as intended purpose, perceived effort, pain or soreness, weather, terrain, and fueling.
4. The skill parses the FIT file when available, compares the confirmed run with the current private profile and plan, and returns the standard analysis report.
5. Every analyzed activity is recorded in SQLite. Compact profile or plan projections change only when the new evidence materially changes the athlete model or active schedule.

For daily recovery data, provide the current morning's sleep and wearable metrics manually. When GarminDB is connected, `collect-daily-metrics` first syncs through yesterday, confirms yesterday's sleep, and adds yesterday's finalized Body Battery/stress to that prior-date record. It then upserts the recovery date in `docs/running_data.db` and refreshes `docs/recovery_metrics.md`. Day-to-day decisions use the most recent seven valid entries; the rolling Markdown view keeps no more than fourteen.

The shared manager handles database operations and projection regeneration:

```bash
python3 .agents/scripts/manage_running_data.py --project-root . verify
python3 .agents/scripts/manage_running_data.py --project-root . context --section all --days 14
python3 .agents/scripts/manage_running_data.py --project-root . history --kind recovery --start-date YYYY-MM-DD --end-date YYYY-MM-DD
python3 .agents/scripts/manage_running_data.py --project-root . render
```

Use `coach-runner` for weekly reviews, development-block planning, pacing, performance growth, or general training questions. It also handles race preparation and strategy when an event is part of the runner's current goals. Use `research-running-gear` for purchases and product comparisons that require current web research.

## What the Project Tracks

- Weekly mileage and run frequency
- Run frequency, sustainable volume, and endurance progression
- Pace, HR, cadence, elevation, and terrain patterns
- Easy-day execution and pacing discipline
- Recovery trends and symptom recurrence
- Fueling practice, shoe mileage, and schedule constraints
- Development-block objectives, benchmarks, and plan adjustments
- Event readiness, specificity, and taper timing when a race is scheduled

The coaching rules favor repeatable consistency and purposeful progression over impressive-looking workouts. The coach should avoid both reckless loading and indefinite undertraining: volume or intensity increases only when the evidence supports them, and every holding pattern needs a reason and reassessment point.

## Public-Repo Safety Check

Before committing or pushing, confirm that:

- `docs/` is ignored and absent from the staged file list.
- No real athlete values were pasted into `AGENTS.md`, `README.md`, or an example file.
- OS files, Python caches, exports, reports, images, and activity files are not staged.
- The example files still say that their contents are synthetic.

If a private file appears in Git status as staged or tracked, stop before pushing and remove it from Git tracking/history as appropriate.

## Sample Daily Metrics Prompt

```
Date: MM/DD/YYYY

Sleep Duration: 00h00m
Sleep score: [number]
Sleep disruption: [none or brief reason]

Resting HR: [number]
HRV overnight: [number]
HRV 7-day average: [number]
HRV status: [label]

Training readiness: [score-number]
Training status: [label]

Soreness/pain: [none, or location + severity 0–10 + improving/same/worse + affects walking/gait yes/no]
Illness or unusual fatigue: [none or brief description]
```

### Copy, paste, and fill in

```
Good morning, here are my daily metrics:

Date:

Sleep Duration:
Sleep score:
Sleep disruption:

Resting HR:
HRV overnight:
HRV 7-day average:
HRV status:

Training readiness:
Training status:

Soreness/pain:
Illness or unusual fatigue:
```
