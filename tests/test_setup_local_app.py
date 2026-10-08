from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SETUP_PATH = (
    ROOT
    / ".agents"
    / "skills"
    / "initialize-running-project"
    / "scripts"
    / "setup_local_app.py"
)
SPEC = importlib.util.spec_from_file_location("setup_local_app", SETUP_PATH)
assert SPEC and SPEC.loader
setup_local_app = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup_local_app
SPEC.loader.exec_module(setup_local_app)


def make_project(root: Path) -> Path:
    for relative in (
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "frontend/package.json",
        "src/running_coach_app/__init__.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    python = root / ".venv" / ("Scripts/python.exe" if setup_local_app.os.name == "nt" else "bin/python3")
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text("", encoding="utf-8")
    return python


class SetupLocalAppTest(unittest.TestCase):
    def test_fresh_setup_creates_virtual_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            python = setup_local_app.virtual_environment_python(root)
            assert python is not None
            python.unlink()
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                command = [str(part) for part in command]
                calls.append(command)
                if command[1:] == ["--version"]:
                    return subprocess.CompletedProcess(command, 0, stdout="v22.12.0\n", stderr="")
                if command[1:3] == ["-m", "venv"]:
                    python.parent.mkdir(parents=True, exist_ok=True)
                    python.write_text("", encoding="utf-8")
                if command[-2:] == ["run", "build"]:
                    built = root / "frontend" / "dist" / "index.html"
                    built.parent.mkdir(parents=True)
                    built.write_text("built", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with mock.patch.object(
                setup_local_app,
                "find_commands",
                return_value=setup_local_app.Commands("node", "npm"),
            ):
                setup_local_app.setup_local_app(root, runner=runner)

        self.assertIn(
            [setup_local_app.sys.executable, "-m", "venv", str(root.resolve() / ".venv")],
            calls,
        )

    def test_supported_node_runs_install_build_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            python = make_project(root)
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append([str(part) for part in command])
                if command[1:] == ["--version"]:
                    return subprocess.CompletedProcess(command, 0, stdout="v22.12.0\n", stderr="")
                if command[-2:] == ["run", "build"]:
                    built = root / "frontend" / "dist" / "index.html"
                    built.parent.mkdir(parents=True)
                    built.write_text("built", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with mock.patch.object(
                setup_local_app,
                "find_commands",
                return_value=setup_local_app.Commands("node", "npm"),
            ):
                setup_local_app.setup_local_app(root, runner=runner)

        self.assertEqual(calls[0], ["node", "--version"])
        self.assertIn([str(python.resolve()), "-m", "pip", "install", "-e", "."], calls)
        self.assertIn(["npm", "ci"], calls)
        self.assertIn(["npm", "run", "build"], calls)
        self.assertIn(
            [str(python.resolve()), "-c", "import fastapi, running_coach_app, uvicorn"],
            calls,
        )

    def test_unsupported_node_defers_without_installing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            calls: list[list[str]] = []

            def runner(command, **kwargs):
                calls.append(command)
                return subprocess.CompletedProcess(command, 0, stdout="v20.17.0\n", stderr="")

            with mock.patch.object(
                setup_local_app,
                "find_commands",
                return_value=setup_local_app.Commands("node", "npm"),
            ):
                with self.assertRaisesRegex(setup_local_app.SetupDeferred, "Node 20.17.0 is unsupported"):
                    setup_local_app.setup_local_app(root, runner=runner)

        self.assertEqual(calls, [["node", "--version"]])

    def test_failed_dependency_command_reports_deferred_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)

            def runner(command, **kwargs):
                if command[1:] == ["--version"]:
                    return subprocess.CompletedProcess(command, 0, stdout="v22.12.0\n", stderr="")
                if command[-2:] == ["npm", "ci"] or command[:2] == ["npm", "ci"]:
                    return subprocess.CompletedProcess(command, 9, stdout="", stderr="network")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with mock.patch.object(
                setup_local_app,
                "find_commands",
                return_value=setup_local_app.Commands("node", "npm"),
            ):
                with self.assertRaisesRegex(
                    setup_local_app.SetupDeferred,
                    "Install frontend dependencies failed with exit code 9",
                ):
                    setup_local_app.setup_local_app(root, runner=runner)

    def test_node_version_boundaries_match_vite_requirement(self) -> None:
        self.assertFalse(setup_local_app.node_version_supported((20, 18, 9)))
        self.assertTrue(setup_local_app.node_version_supported((20, 19, 0)))
        self.assertFalse(setup_local_app.node_version_supported((22, 11, 9)))
        self.assertTrue(setup_local_app.node_version_supported((22, 12, 0)))
        self.assertTrue(setup_local_app.node_version_supported((24, 0, 0)))


if __name__ == "__main__":
    unittest.main()
