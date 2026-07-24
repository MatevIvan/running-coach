# Privacy-First Marathon Training Analyst

This repository turns Codex into a persistent running-performance analyst and marathon coach. It combines Garmin/Strava activity data, recovery metrics, a living runner profile, and an adaptive marathon plan while keeping the athlete's personal data outside Git.

The project is designed for evidence-based run reviews, recovery-aware planning, durability tracking, and direct injury-risk management. It is not medical software and does not diagnose health conditions.

## Privacy Model

All real athlete data lives in `docs/`, which is ignored by Git. This includes:

- The live runner profile and marathon plan
- Raw and rolling recovery logs
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
│   ├── marathon_plan.md              # Active plan and current week
│   ├── recovery_metrics_raw.json     # Permanent recovery history
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
├── marathon_plan_example.md          # Synthetic structure example
├── recovery_metrics_raw_example.json # Synthetic raw-log example
└── recovery_metrics_example.md       # Synthetic rolling-view example
```

The root example files are documentation only. `AGENTS.md` explicitly prohibits treating them as real athlete data.

## How Project Instructions Work

`AGENTS.md` is the project constitution. It gives every chat the shared privacy boundary, live-file locations, durable-record contract, and common coaching standards. See the official [AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Each folder under `.agents/skills/` contains a specialized prompt in `SKILL.md`. Codex scans this repository location automatically. The skill description supports implicit selection: when a request matches it, Codex loads that skill's detailed workflow. `AGENTS.md` also contains a compact routing table so the intended relationship remains explicit and understandable. See the official [skills documentation](https://learn.chatgpt.com/docs/build-skills).

The current roles are:

- `initialize-running-project`: create the ignored private workspace, collect the initial athlete baseline, and optionally install and import GarminDB.
- `collect-daily-metrics`: record and interpret recovery data.
- `analyze-running-activity`: review a completed run and decide whether the plan or profile changes.
- `coach-runner`: answer coaching questions and maintain the broader plan and athlete model.
- `research-running-gear`: research current products against athlete-specific needs.
- `parse-fit-run`: parse FIT files for the activity-analysis workflow.

This keeps global context small and loads scenario-specific instructions only when needed.

## Getting Started

1. Clone the repository.
2. Open the repository as a Codex project.
3. Ask Codex: `Use $initialize-running-project to set up this project for me.`
4. Choose whether to connect GarminDB, then complete the short athlete questionnaire.
5. If GarminDB is selected, edit credentials only in the generated private file when prompted; never paste them into chat.
6. Put any other Garmin/Strava exports and future FIT/GPX activities under `docs/`.

If the private working files do not exist, Codex should report that live athlete data is unavailable. It should never fall back to the synthetic examples.

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
5. Durable private files change only when the new evidence materially changes the athlete model or active schedule.

For daily recovery data, `collect-daily-metrics` updates `docs/recovery_metrics_raw.json` first and then refreshes the compact `docs/recovery_metrics.md` view. Day-to-day decisions use the most recent seven valid entries; the rolling Markdown view keeps no more than fourteen.

Use `coach-runner` for weekly reviews, planning, marathon readiness, pacing, or general training questions. Use `research-running-gear` for purchases and product comparisons that require current web research.

## What the Project Tracks

- Weekly mileage and run frequency
- Long-run progression and marathon durability
- Pace, HR, cadence, elevation, and terrain patterns
- Easy-day execution and pacing discipline
- Recovery trends and symptom recurrence
- Fueling practice, shoe mileage, and schedule constraints
- Race readiness, taper timing, and plan adjustments

The coaching rules favor repeatable consistency over impressive-looking workouts. Harder training is added only when the data supports it.

## Public-Repo Safety Check

Before committing or pushing, confirm that:

- `docs/` is ignored and absent from the staged file list.
- No real athlete values were pasted into `AGENTS.md`, `README.md`, or an example file.
- OS files, Python caches, exports, reports, images, and activity files are not staged.
- The example files still say that their contents are synthetic.

If a private file appears in Git status as staged or tracked, stop before pushing and remove it from Git tracking/history as appropriate.
