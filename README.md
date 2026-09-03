# Privacy-First Running Coach

This repository equips repository-capable coding agents to act as persistent running-performance analysts and coaches. It combines Garmin/Strava activity data, recovery metrics, a living runner profile, and an adaptive running plan while keeping the athlete's personal data outside Git.

The project is designed to track runs, explain what the training is doing, and plan progressive work that helps the runner improve in a healthy, sustainable way. A race can shape the plan when one is scheduled, but no race is required: without one, the coach uses development blocks, measurable objectives, and dated reassessments. It is not medical software and does not diagnose health conditions.

## Privacy Model

All real athlete data lives in `docs/`, which is ignored by Git. This includes:

- The private SQLite history and compact runner-profile, running-plan, and recovery projections
- FIT, GPX, CSV, screenshot, and export data
- Generated athlete reports and any other derived personal documents

Only reusable instructions, tooling, and synthetic examples belong in the public repository. Never force-add `docs/` or copy personal values into an example file.

Automatic run-weather lookup sends one representative route coordinate, quantized to a 0.05-degree grid, plus the activity date to the [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api). Exact and representative coordinates are not displayed or stored in `running_data.db`. Request an offline/no-weather analysis to skip this network lookup.

Important: `.gitignore` prevents untracked files from being added normally, but it cannot remove data that was already committed. Run a Git status check before every public push, and treat any previously committed personal data as a history-cleanup incident.

## Repository Layout

```text
.
├── AGENTS.md                         # Canonical agent context, privacy, and routing
├── CLAUDE.md                         # Claude adapter importing AGENTS.md
├── GEMINI.md                         # Gemini adapter importing AGENTS.md
├── .github/copilot-instructions.md   # Copilot adapter importing AGENTS.md
├── .claude/skills/                   # Claude discovery proxies to canonical skills
├── .agents/                          # Canonical skills, scripts, and data contract
│   └── skills/
│       ├── initialize-running-project/ # GarminDB-first setup and athlete onboarding
│       ├── collect-daily-metrics/    # Daily recovery collection and decisions
│       ├── analyze-running-activity/ # Run review with historical weather lookup
│       ├── coach-runner/             # Planning and coaching conversations
│       ├── research-running-gear/    # Current purchase research
│       └── parse-fit-run/            # Dependency-free FIT activity parser
├── .gitignore                        # Excludes private data and local settings
├── docs/                             # Private local workspace; never committed
│   ├── runner_profile.md             # Living athlete model
│   ├── running_plan.md               # Active plan, current week, and development horizon
│   ├── running_data.db                # Durable recovery, profile, activity, and plan history
│   ├── recovery_metrics.md           # Rolling 14-day recovery view
│   ├── activities/                   # New FIT/GPX activities
│   └── ...                           # Exports, reports, screenshots, and notes
├── runner_profile_example.md         # Synthetic structure example
├── running_plan_example.md           # Synthetic structure example
└── recovery_metrics_example.md       # Synthetic rolling-view example
```

The root example files are documentation only. `AGENTS.md` explicitly prohibits treating them as real athlete data.

## How Agent Instructions Work

`AGENTS.md` is the canonical project constitution. It gives every compatible agent the shared privacy boundary, database and projection contracts, coaching standards, and task-routing rules. The format is an open convention for repository agents; see [AGENTS.md](https://agents.md/).

Each folder under `.agents/skills/` contains the canonical `SKILL.md` for one specialized workflow. These files follow the open [Agent Skills specification](https://agentskills.io/specification). A harness that discovers `.agents/skills/` can load them directly. A harness without native discovery must use the routing table in `AGENTS.md`, read the matching skill completely, and then follow it.

Vendor adapters contain discovery instructions only:

- Claude loads `CLAUDE.md` and discovers regular-file proxies under `.claude/skills/`; each proxy directs it to the canonical `.agents/skills/` directory.
- Gemini loads `GEMINI.md` and discovers `.agents/skills/` as a supported workspace alias.
- GitHub Copilot loads its repository adapter or `AGENTS.md` and supports `.agents/skills/` directly on skill-capable surfaces.
- Cursor and other `AGENTS.md` consumers use the root instructions without a duplicate rules file.

The optional `agents/openai.yaml` files provide Codex interface metadata only. They do not contain canonical workflow behavior. When a canonical skill's `name` or `description` changes, update the same metadata in its Claude proxy; all procedural changes belong only in `.agents/skills/`.

| Harness | Project instructions | Skill discovery | Typical invocation |
| --- | --- | --- | --- |
| Codex | `AGENTS.md` | `.agents/skills/` | `Use $initialize-running-project ...` or natural language |
| Claude Code / Agent SDK | `CLAUDE.md` imports `AGENTS.md` | `.claude/skills/` proxies | `/initialize-running-project` or natural language |
| Gemini CLI | `GEMINI.md` imports `AGENTS.md` | `.agents/skills/` | `/initialize-running-project` or natural language |
| GitHub Copilot | `AGENTS.md` and `.github/copilot-instructions.md` | `.agents/skills/` on supported surfaces | `/initialize-running-project` where available, or natural language |
| Cursor | `AGENTS.md` | Routing table and canonical skill files | Natural language |
| Other `AGENTS.md` consumers | `AGENTS.md` | Routing table and canonical skill files | Natural language |

The current roles are:

- `initialize-running-project`: create the ignored private workspace, prioritize GarminDB installation and import, derive the objective baseline, and then collect only the remaining athlete context.
- `collect-daily-metrics`: record and interpret recovery data.
- `analyze-running-activity`: review a completed run, retrieve its historical weather, and decide whether the plan or profile changes.
- `coach-runner`: answer coaching questions and maintain the broader plan and athlete model.
- `research-running-gear`: research current products against athlete-specific needs.
- `parse-fit-run`: parse FIT files for the activity-analysis workflow.

This keeps global context small and loads scenario-specific instructions only when needed.

## Planning Model

`docs/running_data.db` stores the durable athlete history. `docs/runner_profile.md` is a compact current projection containing the athlete's continuing development goals and an explicit `Goals and Event Context` section. That section records `none` when no event is planned; when a race is relevant, it records the date, distance, course context, and finish-versus-performance priority.

`docs/running_plan.md` is a compact projection that always has a current week, a broader development objective, and a dated reassessment point. Completed weeks and superseded adjustments remain queryable in SQLite rather than accumulating in Markdown. Without a race, it uses a 4-12 week development block with measurable progression criteria. With a confirmed race, it adds only the event-specific work, taper, rehearsal, and recovery that the event actually requires.

GarminDB remains the complete read-only source for raw wearable data. Initialization projects only coaching-ready evidence into `docs/running_data.db`: recent normalized recovery days, reviewed weekly or monthly training summaries, and durable profile conclusions. Unreviewed activities remain in GarminDB; an individual run enters `activity_reviews` only after the activity-analysis workflow adds the required qualitative context and coaching interpretation.

## Command-Line Compatibility

The repository's executable tooling is Python rather than Bash and is designed to support macOS, Linux, and Windows. Command examples using `python3` mean an available Python 3 interpreter. On Windows, use `py -3` or `python`; virtual-environment executables live under `.venv\Scripts\` instead of `.venv/bin/`. Replace `python3` in one-line examples, and use the explicit PowerShell blocks in the GarminDB setup rather than copying Bash line continuations.

For example, initialize the private workspace on Windows when GarminDB was selected with:

```powershell
py -3 .agents\skills\initialize-running-project\scripts\initialize_private_workspace.py --project-root . --with-garmindb
```

The GarminDB setup creates `.venv` and installs `tzdata`. If GarminDB is skipped but FIT parsing or weather lookup needs a named time zone, create the same virtual environment with `py -3 -m venv .venv`, install `tzdata` through `.venv\Scripts\python.exe`, and use that interpreter for the project scripts.

Windows does not apply POSIX `0600`/`0700` modes as file ACLs. Keep the repository in a private user-owned location and inspect the inherited permissions with `Get-Acl .\docs` if the computer or workspace is shared. Git exclusion still applies on every platform.

## Getting Started

1. Clone the repository.
2. Open the repository in a supported repository agent.
3. Ask: `Use the initialize-running-project skill to set up this project for me.` Use `$initialize-running-project` in Codex or `/initialize-running-project` on slash-command surfaces when you prefer explicit invocation.
4. Choose whether to connect GarminDB. When selected, the agent installs and imports GarminDB, analyzes the available objective history, and only then asks the short qualitative questionnaire.
5. If GarminDB is selected, edit credentials only in the generated private file when prompted; never paste them into chat.
6. Put any other Garmin/Strava exports and future FIT/GPX activities under `docs/`.

If the private database or current projections do not exist, the agent must report that live athlete data is unavailable. It must never fall back to the synthetic examples.

## FIT Activity Parsing

The bundled parser extracts record-derived distance, time, pace, HR, cadence, power, splits, HR-zone distribution, and first-half/second-half comparisons from a running FIT file. During a run review, a companion helper reads GPS points privately, sends only a quantized representative location to the historical-weather service, and never displays or stores route coordinates.

Human-readable output:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py docs/activities/example.fit
```

Machine-readable output:

```bash
python3 .agents/skills/parse-fit-run/scripts/parse_fit_run.py docs/activities/example.fit --json
```

The parser otherwise uses only Python's standard library. Windows Python installations commonly need the `tzdata` package for named IANA time zones; the GarminDB setup installs it in the project virtual environment.

## Normal Workflow

For a new run:

1. Ask `analyze-running-activity` to review the run. When GarminDB is connected, it first performs an incremental activity sync; otherwise, add the activity file under `docs/activities/` or provide its details in the conversation.
2. The skill resolves an unambiguous candidate automatically and asks only when multiple activities plausibly match.
3. When GPS data is available, the skill derives a privacy-limited route location and retrieves historical temperature, apparent temperature, humidity, dew point, precipitation, wind, and gusts for the activity window.
4. Answer its short follow-up about information the device and weather archive do not know, such as intended purpose, perceived effort, pain or soreness, surface/footing, unusual localized exposure, and fueling.
5. The skill parses the FIT file when available, compares the confirmed run and retrieved weather with the current private profile and plan, and returns the standard analysis report.
6. Every analyzed activity is recorded in SQLite, including the weather provenance when retrieved. Compact profile or plan projections change only when the new evidence materially changes the athlete model or active schedule.

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

## Sample Run Analysis Prompt

```
Analyze today's run.

Run purpose:


Route/terrain:


Execution notes:
Felt easy/moderate/hard:
Any pain/tightness during run:

Any stops/walk breaks:
Fuel/hydration used:
Anything unusual:
```
