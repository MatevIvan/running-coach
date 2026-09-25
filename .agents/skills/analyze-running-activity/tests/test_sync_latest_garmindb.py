#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_latest_garmindb.py"
SPEC = importlib.util.spec_from_file_location("sync_latest_garmindb", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class SyncLatestGarminDbTests(unittest.TestCase):
    def test_network_failure_takes_priority_over_login_text(self) -> None:
        output = (
            "login failed: All login strategies exhausted: "
            "Could not resolve host: sso.garmin.com"
        )

        category, _ = sync.classify_failure(output)

        self.assertEqual(category, "network")
        self.assertTrue(sync.has_terminal_failure(output))

    def test_cached_token_warning_is_not_terminal(self) -> None:
        output = "cached Garmin Connect token login failed; falling back to credential login"

        self.assertFalse(sync.has_terminal_failure(output))

    def test_reads_only_new_log_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "garmindb.log"
            log_path.write_text("old failure\n", encoding="utf-8")
            start = sync.log_size(log_path)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("new failure\n")

            self.assertEqual(sync.read_log_delta(log_path, start), "new failure\n")

    def test_network_failures_retry_with_exponential_backoff(self) -> None:
        outcomes = iter(
            (
                subprocess.CompletedProcess([], 1, "Could not resolve host"),
                subprocess.CompletedProcess([], 1, "Network is unreachable"),
                subprocess.CompletedProcess([], 0, "sync complete"),
            )
        )
        calls: list[list[str]] = []
        sleeps: list[float] = []

        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return next(outcomes)

        with tempfile.TemporaryDirectory() as directory:
            completed, diagnostics, attempts, delays = sync.run_with_network_backoff(
                ["garmindb"],
                Path(directory),
                Path(directory) / "garmindb.log",
                max_attempts=3,
                initial_backoff_seconds=0.5,
                max_backoff_seconds=5.0,
                runner=runner,
                sleeper=sleeps.append,
            )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(diagnostics, "sync complete")
        self.assertEqual(attempts, 3)
        self.assertEqual(delays, [0.5, 1.0])
        self.assertEqual(sleeps, [0.5, 1.0])
        self.assertEqual(len(calls), 3)

    def test_non_network_failure_does_not_retry(self) -> None:
        sleeps: list[float] = []

        def runner(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess([], 1, "authentication failed")

        with tempfile.TemporaryDirectory() as directory:
            completed, _, attempts, delays = sync.run_with_network_backoff(
                ["garmindb"],
                Path(directory),
                Path(directory) / "garmindb.log",
                max_attempts=4,
                initial_backoff_seconds=1.0,
                max_backoff_seconds=8.0,
                runner=runner,
                sleeper=sleeps.append,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(attempts, 1)
        self.assertEqual(delays, [])
        self.assertEqual(sleeps, [])

    def test_backoff_delay_is_capped(self) -> None:
        self.assertEqual(sync.backoff_delay(1, 2.0, 5.0), 2.0)
        self.assertEqual(sync.backoff_delay(2, 2.0, 5.0), 4.0)
        self.assertEqual(sync.backoff_delay(3, 2.0, 5.0), 5.0)


if __name__ == "__main__":
    unittest.main()
