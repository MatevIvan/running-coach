from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INITIALIZER = ROOT / ".agents" / "skills" / "initialize-running-project" / "scripts" / "initialize_private_workspace.py"


class InitializeWorkspaceTest(unittest.TestCase):
    def test_fresh_workspace_creates_database_without_raw_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "AGENTS.md").write_text("test\n", encoding="utf-8")
            (project / ".gitignore").write_text("/docs/\n", encoding="utf-8")
            scripts = project / ".agents" / "scripts"
            migrations = project / ".agents" / "running_data" / "migrations"
            scripts.mkdir(parents=True)
            migrations.mkdir(parents=True)
            shutil.copy2(ROOT / ".agents" / "scripts" / "manage_running_data.py", scripts)
            shutil.copy2(ROOT / ".agents" / "running_data" / "migrations" / "001_initial.sql", migrations)

            result = subprocess.run(
                [sys.executable, str(INITIALIZER), "--project-root", str(project)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            docs = project / "docs"
            self.assertTrue((docs / "running_data.db").is_file())
            self.assertFalse((docs / "recovery_metrics_raw.json").exists())
            for name in ("runner_profile.md", "running_plan.md", "recovery_metrics.md"):
                self.assertTrue((docs / name).is_file())
            connection = sqlite3.connect(docs / "running_data.db")
            count = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
            self.assertEqual(count, 13)


if __name__ == "__main__":
    unittest.main()
