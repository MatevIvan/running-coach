# GarminDB Setup Branch

Follow this reference only after the user opted into GarminDB.

## Contents

1. Collect setup choices
2. Check Python and install
3. Create the private configuration
4. Run the initial import
5. Verify narrowly
6. Return the verified import

## 1. Collect Setup Choices

Ask for:

- the earliest date desired for sleep, RHR, HRV, and monitoring data;
- the approximate maximum number of activities to download;
- metric or statute display units;
- whether weight data should be enabled;
- credential storage mode.

GarminDB uses dates for daily health data but a count for activities. If the user only gives a time horizon, estimate an activity cap from their stated training frequency with a generous buffer and disclose the cap. Reasonable starting caps are 150 for six months, 300 for one year, 600 for two years, and 1,500 for a longer history. Increase them for frequent cycling, walking, or multisport recording.

Offer these credential modes:

1. `macos-keychain` on macOS: preferred when the Garmin password is already stored as an Internet Password for `sso.garmin.com`.
2. `password-file`: portable and private; store the password in `docs/garmindb/.garmin_password` with restrictive permissions.
3. `config`: simplest, but stores the password directly in the ignored JSON configuration.

Never request a password or MFA code in the conversation.

On Windows, the password file and configuration inherit the containing folder's ACL. Keep the repository in a private user-owned location and have the user review that ACL when the computer or workspace is shared; do not claim that a POSIX `0600` request secures a Windows file.

## 2. Check Python and Install

Use the PyPI release unless the user explicitly requests GarminDB source development. The PyPI path avoids nesting another Git repository inside the private data directory.

Check Python first. GarminDB 3.8.0 requires Python 3.12 or newer; if the current release changes that constraint, follow the installer error and current package metadata.

From the project root on macOS/Linux:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install GarminDb tzdata
.venv/bin/python .venv/bin/garmindb_cli.py --version
```

From Windows PowerShell:

```powershell
py -3 --version
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install GarminDb tzdata
& .\.venv\Scripts\python.exe .\.venv\Scripts\garmindb_cli.py --version
```

Inspect the installed authentication dependency:

```bash
.venv/bin/python -c "import importlib.metadata as m; print('GarminDb', m.version('GarminDb')); print('garminconnect', m.version('garminconnect'))"
```

```powershell
& .\.venv\Scripts\python.exe -c "import importlib.metadata as m; print('GarminDb', m.version('GarminDb')); print('garminconnect', m.version('garminconnect'))"
```

GarminDB 3.8.0 installs `garminconnect==0.3.3`. That authentication version failed on a stale-token/social-profile path in project testing. `garminconnect` 0.3.5 added token-store security and login-recovery fixes, and the current GarminDB source accepts `garminconnect>=0.3.3`.

When the released GarminDB package still installs a `garminconnect` version older than 0.3.5, apply this temporary tested override:

```bash
.venv/bin/python -m pip install --upgrade "garminconnect==0.3.5"
```

```powershell
& .\.venv\Scripts\python.exe -m pip install --upgrade "garminconnect==0.3.5"
```

GarminDB 3.8.0's published metadata will cause `pip check` to report its old exact `==0.3.3` requirement even though the 0.3.5 API passed the project's import and live incremental-sync tests. Treat the override as provisional: verify a real guarded sync before keeping it, roll back through the platform's virtual-environment Python with `-m pip install "garminconnect==0.3.3"` if compatibility fails, and remove this workaround when a released GarminDB version officially allows the fixed dependency. Check current upstream release notes rather than assuming these version numbers remain current.

Preserve an existing `.venv`. Inspect it before installing and do not delete or rebuild it without explicit approval. Installing packages and downloading Garmin data require network access. If the current harness cannot obtain network access, defer the GarminDB install or import, report the blocked step precisely, and leave the core private workspace usable.

## 3. Create the Private Configuration

Create the configuration without overwriting an existing one:

```bash
python3 .agents/skills/initialize-running-project/scripts/setup_garmindb_config.py \
  --project-root . create \
  --start-date YYYY-MM-DD \
  --activity-count 300 \
  --units statute \
  --credential-mode password-file
```

Windows PowerShell equivalent:

```powershell
py -3 .agents\skills\initialize-running-project\scripts\setup_garmindb_config.py --project-root . create --start-date YYYY-MM-DD --activity-count 300 --units statute --credential-mode password-file
```

Add `--enable-weight` only when requested. Replace the example arguments with the user’s choices. Online Garmin Connect imports do not use a mounted-device path. If local USB-device copying is needed, pass `--mount-dir PATH`; without it, the generated configuration uses `/Volumes/GARMIN` on macOS and a harmless private placeholder on other platforms.

The command creates `docs/garmindb/GarminConnectConfig.json`, points all generated data at `docs/garmindb/data`, and optionally creates the private password file.

Show the user only the file paths and fields they must edit:

- Always fill `credentials.user` in `docs/garmindb/GarminConnectConfig.json`.
- For `config`, fill `credentials.password` in that JSON file.
- For `password-file`, put only the password in `docs/garmindb/.garmin_password`.
- For `macos-keychain`, leave the JSON password blank and ensure the Login Keychain contains an Internet Password for `sso.garmin.com`.

Pause until the user confirms the local credential edit is complete. Do not open, print, quote, or summarize the credential value.

Validate without revealing secrets:

```bash
python3 .agents/skills/initialize-running-project/scripts/setup_garmindb_config.py \
  --project-root . validate
```

```powershell
py -3 .agents\skills\initialize-running-project\scripts\setup_garmindb_config.py --project-root . validate
```

## 4. Run the Initial Import

Run from the private GarminDB working directory so logs and tokens remain under ignored `docs/`:

```bash
cd docs/garmindb
../../.venv/bin/python ../../.venv/bin/garmindb_cli.py --config . --all --download --import --analyze
```

Windows PowerShell equivalent:

```powershell
Push-Location .\docs\garmindb
& ..\..\.venv\Scripts\python.exe ..\..\.venv\Scripts\garmindb_cli.py --config . --all --download --import --analyze
Pop-Location
```

Do not add `--latest` to the initial historical import. Use it for later incremental syncs:

```bash
cd docs/garmindb
../../.venv/bin/python ../../.venv/bin/garmindb_cli.py --config . --all --download --import --analyze --latest
```

```powershell
Push-Location .\docs\garmindb
& ..\..\.venv\Scripts\python.exe ..\..\.venv\Scripts\garmindb_cli.py --config . --all --download --import --analyze --latest
Pop-Location
```

The first login may require the user to complete MFA or a Keychain prompt. Stay available while the initial command runs, give brief progress updates, and do not start duplicate imports.

## 5. Verify Narrowly

Do not read the entire potentially large log. Check:

- the command exit status;
- whether `docs/garmindb/data/DBs/` contains SQLite databases;
- `stats.txt` or the final command summary when available;
- a targeted search for `ERROR`, `Failed to parse`, authentication failures, or tracebacks;
- `PRAGMA quick_check` on each created SQLite database;
- whether Git still ignores every path under `docs/`.

Separate harmless unsupported FIT messages from failures that omit an activity, lap, record stream, or daily metric. Report partial imports precisely.

## 6. Return the Verified Import

Return only non-secret setup facts to the main initialization workflow: GarminDB version, requested date horizon, activity cap, enabled statistics, database directory, actual per-stream coverage, and whether validation passed. Do not treat the GarminDB branch as complete until the main workflow has processed the imported history through `garmindb-bootstrap-analysis.md`.

Do not copy Garmin credentials, tokens, route data, health values, or database contents into tracked files. Future syncs should use the incremental `--latest` command.
