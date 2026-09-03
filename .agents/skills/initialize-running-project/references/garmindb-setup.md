# GarminDB Setup Branch

Follow this reference only after the user opted into GarminDB.

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

Never request a password or MFA code in chat.

## 2. Check Python and Install

Use the PyPI release unless the user explicitly requests GarminDB source development. The PyPI path avoids nesting another Git repository inside the private data directory.

Check Python first. GarminDB 3.8.0 requires Python 3.12 or newer; if the current release changes that constraint, follow the installer error and current package metadata.

From the project root:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install GarminDb
.venv/bin/garmindb_cli.py --version
```

Inspect the installed authentication dependency:

```bash
.venv/bin/python -c "import importlib.metadata as m; print('GarminDb', m.version('GarminDb')); print('garminconnect', m.version('garminconnect'))"
```

GarminDB 3.8.0 installs `garminconnect==0.3.3`. That authentication version failed on a stale-token/social-profile path in project testing. `garminconnect` 0.3.5 added token-store security and login-recovery fixes, and the current GarminDB source accepts `garminconnect>=0.3.3`.

When the released GarminDB package still installs a `garminconnect` version older than 0.3.5, apply this temporary tested override:

```bash
.venv/bin/python -m pip install --upgrade "garminconnect==0.3.5"
```

GarminDB 3.8.0's published metadata will cause `pip check` to report its old exact `==0.3.3` requirement even though the 0.3.5 API passed the project's import and live incremental-sync tests. Treat the override as provisional: verify a real guarded sync before keeping it, roll back with `.venv/bin/python -m pip install "garminconnect==0.3.3"` if compatibility fails, and remove this workaround when a released GarminDB version officially allows the fixed dependency. Check current upstream release notes rather than assuming these version numbers remain current.

On Windows, use the equivalent executables under `.venv\Scripts\`.

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

Add `--enable-weight` only when requested. Replace the example arguments with the user’s choices.

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

## 4. Run the Initial Import

Run from the private GarminDB working directory so logs and tokens remain under ignored `docs/`:

```bash
cd docs/garmindb
../../.venv/bin/garmindb_cli.py --config . --all --download --import --analyze
```

Do not add `--latest` to the initial historical import. Use it for later incremental syncs:

```bash
cd docs/garmindb
../../.venv/bin/garmindb_cli.py --config . --all --download --import --analyze --latest
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

## 6. Hand Off

Record only non-secret setup facts in the final response: GarminDB version, date horizon, activity cap, enabled statistics, database directory, and whether validation passed.

Do not copy Garmin credentials, tokens, route data, health values, or database contents into tracked files. Future syncs should use the incremental `--latest` command.
