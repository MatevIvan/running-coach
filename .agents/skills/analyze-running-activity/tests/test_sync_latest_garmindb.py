#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
