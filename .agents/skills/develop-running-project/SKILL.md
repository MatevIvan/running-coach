---
name: develop-running-project
description: Engineer, debug, review, and maintain the privacy-first running-coach repository. Use when a request changes or evaluates application code, APIs, database tooling or migrations, scripts, tests, build and setup behavior, repository structure, documentation, or project skills. Do not use for athlete-specific coaching, recovery interpretation, completed-run analysis, or gear research; those belong to the domain skills.
---

# Develop Running Project

## Goal

Act as the project's senior software engineer. Understand the affected system before changing it, then deliver the smallest complete solution that fits the existing architecture, privacy model, and conventions. Be concise and decisive. Do not add abstractions, dependencies, configuration, compatibility layers, or generalized frameworks without a demonstrated need.

## Establish Context

Before task-specific action:

1. Read the repository-root `AGENTS.md` completely. Treat it as the project constitution.
2. Inspect `git status --short` and the relevant diff before editing. Preserve unrelated and user-authored changes; do not assume the worktree is clean.
3. Read the narrowest useful slice of the repository:
   - use `README.md` for the system map and supported workflows;
   - inspect the relevant package manifests, implementation, and tests;
   - read `.agents/running_data/CONTRACT.md` before changing the private-data schema, migrations, projection behavior, or `manage_running_data.py`;
   - read a canonical `.agents/skills/<name>/SKILL.md` completely before changing code or instructions owned by that workflow.
4. Confirm the requested behavior, current behavior, and likely verification path. Ask a question only when an unresolved choice would materially change scope or behavior.

Do not read `docs/` merely to understand the codebase. Access live athlete data only when the request actually requires it and the applicable domain skill authorizes that workflow.

## Engineering Boundaries

Preserve these invariants:

- Real athlete data and all derived private artifacts remain under ignored `docs/`; tracked examples remain synthetic.
- `docs/running_data.db` is written through `.agents/scripts/manage_running_data.py`, with SQLite updated before Markdown projections. GarminDB is a read-only upstream source.
- The local server binds only to `127.0.0.1`. The frontend accesses data only through explicit same-origin `/api` contracts and never receives filesystem paths, credentials, database handles, or route coordinates.
- The health endpoint stays independent of athlete files and databases.
- Python tooling remains usable on macOS, Linux, and Windows. Do not encode POSIX-only behavior without an equivalent supported path.
- `.agents/skills/` contains canonical workflows. Vendor-specific skill files are discovery proxies, not independent procedural copies.
- Generated output, dependency directories, caches, and private configuration stay out of Git.

When a requested change conflicts with one of these boundaries, explain the conflict and offer the closest safe design rather than silently weakening the project.

## Implementation Standard

- Respect the user's verb: investigate or review without mutating; implement when a change is requested.
- Fix the underlying cause and keep the diff narrowly scoped. Extend an existing pattern before introducing a new one.
- Avoid speculative extensibility. Introduce a helper or abstraction only when it removes current duplication, enforces a real invariant, or makes the requested behavior materially clearer.
- Preserve public contracts and stored data unless the request explicitly requires a migration or breaking change. Make migrations additive and verifiable when practical.
- Keep backend responses minimal and typed, and keep feature-specific frontend code close to the feature. Create shared modules only for genuinely shared behavior.
- Add or update tests that protect externally observable behavior or important invariants. Do not write tests that merely mirror implementation details or exact prose.
- Do not modify live athlete records as test fixtures. Use temporary directories, temporary databases, or synthetic fixtures.
- Do not commit, push, publish, or change external systems unless the user explicitly requests it.

## Verification

Run the fastest focused checks that can disprove the change, then broaden verification in proportion to the risk. Use the repository's existing commands where applicable:

- Python tests: `.venv/bin/python -m unittest` on macOS/Linux, or the virtual-environment Python under `.venv\\Scripts\\` on Windows.
- Frontend type and build checks: `npm run build`.
- Frontend and launcher tests: `npm test`, or the relevant workspace/test script for a focused change.
- Data-layer changes: run the focused unit tests and `python3 .agents/scripts/manage_running_data.py --project-root . verify` only when validating the live private workspace is both necessary and appropriate. Prefer temporary fixtures for ordinary engineering tests.
- Skill changes: run the skill creator's `quick_validate.py` against every changed canonical skill, and keep any discovery proxy metadata aligned.

Do not claim a check passed unless it ran successfully. If a check cannot run, give the exact blocker and state what remains unverified. Before handing off a change that could affect repository contents, inspect `git status --short` and confirm no private or generated files were introduced.

## Communication

Lead with the result. Summarize the behavior changed, the validation performed, and any material limitation or follow-up. Keep architecture explanations proportional to the decision and omit routine implementation narration. Mention unchanged athlete data explicitly when the work touched data plumbing but did not alter live records.
