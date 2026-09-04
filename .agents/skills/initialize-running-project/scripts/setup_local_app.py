#!/usr/bin/env python3
"""Install and verify the optional local UI without touching private athlete data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Callable, Sequence


NODE_REQUIREMENT = "^20.19.0 || >=22.12.0"
Runner = Callable[..., subprocess.CompletedProcess[str]]


class SetupDeferred(RuntimeError):
    """A recoverable setup problem that must not block coaching initialization."""


@dataclass(frozen=True)
class Commands:
    node: str
    npm: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set up the optional local Running Coach application."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing package.json and pyproject.toml.",
    )
    return parser.parse_args()


def parse_node_version(output: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", output.strip())
    if not match:
        raise SetupDeferred(f"Could not parse Node version: {output.strip()!r}.")
    return tuple(int(part) for part in match.groups())


def node_version_supported(version: tuple[int, int, int]) -> bool:
    major, minor, patch = version
    if major == 20:
        return (minor, patch) >= (19, 0)
    if major == 22:
        return (minor, patch) >= (12, 0)
    return major > 22


def find_commands() -> Commands:
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node:
        raise SetupDeferred(
            f"Node is not installed. Install a version matching {NODE_REQUIREMENT}."
        )
    if not npm:
        raise SetupDeferred("npm is not installed or is not available on PATH.")
    return Commands(node=node, npm=npm)


def virtual_environment_python(root: Path) -> Path | None:
    candidates = (
        (root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "Scripts" / "python3.exe")
        if os.name == "nt"
        else (root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python")
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def format_command(command: Sequence[str]) -> str:
    parts = [str(part) for part in command]
    return subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    runner: Runner,
    stage: str,
) -> None:
    printable_command = format_command(command)
    print(f"{stage}: {printable_command}")
    try:
        result = runner(
            list(map(str, command)),
            cwd=cwd,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SetupDeferred(f"{stage} could not start: {exc}") from exc
    if result.returncode != 0:
        raise SetupDeferred(
            f"{stage} failed with exit code {result.returncode}: "
            f"{printable_command}"
        )


def require_project_files(root: Path) -> None:
    missing = [
        path
        for path in (
            root / "pyproject.toml",
            root / "package.json",
            root / "package-lock.json",
            root / "frontend" / "package.json",
            root / "src" / "running_coach_app" / "__init__.py",
        )
        if not path.is_file()
    ]
    if missing:
        paths = ", ".join(str(path.relative_to(root)) for path in missing)
        raise SetupDeferred(f"Required application files are missing: {paths}.")


def setup_local_app(root: Path, runner: Runner = subprocess.run) -> None:
    root = root.expanduser().resolve()
    require_project_files(root)
    if sys.version_info < (3, 12):
        actual = ".".join(map(str, sys.version_info[:3]))
        raise SetupDeferred(
            f"Python {actual} is unsupported. Install Python 3.12 or newer."
        )
    commands = find_commands()

    try:
        version_result = runner(
            [commands.node, "--version"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise SetupDeferred(f"Could not run `node --version`: {exc}") from exc
    if version_result.returncode != 0:
        raise SetupDeferred("Could not run `node --version`.")
    version = parse_node_version(version_result.stdout)
    if not node_version_supported(version):
        actual = ".".join(map(str, version))
        raise SetupDeferred(
            f"Node {actual} is unsupported. Install Node {NODE_REQUIREMENT}, then rerun "
            "this setup helper; system Node is never upgraded automatically."
        )

    python = virtual_environment_python(root)
    if python is None:
        run_command(
            [sys.executable, "-m", "venv", root / ".venv"],
            cwd=root,
            runner=runner,
            stage="Create virtual environment",
        )
        python = virtual_environment_python(root)
        if python is None:
            raise SetupDeferred(
                "Virtual environment creation completed but its Python interpreter was not found."
            )
    else:
        print(f"Preserve virtual environment: {root / '.venv'}")

    run_command(
        [python, "-m", "pip", "install", "-e", "."],
        cwd=root,
        runner=runner,
        stage="Install backend",
    )
    run_command(
        [commands.npm, "ci"],
        cwd=root,
        runner=runner,
        stage="Install frontend dependencies",
    )
    run_command(
        [commands.npm, "run", "build"],
        cwd=root,
        runner=runner,
        stage="Build frontend",
    )
    run_command(
        [python, "-c", "import fastapi, running_coach_app, uvicorn"],
        cwd=root,
        runner=runner,
        stage="Verify backend",
    )

    built_index = root / "frontend" / "dist" / "index.html"
    if not built_index.is_file():
        raise SetupDeferred(
            f"Frontend build command succeeded but {built_index} was not created."
        )


def main() -> int:
    args = parse_args()
    try:
        setup_local_app(Path(args.project_root))
    except SetupDeferred as exc:
        print(f"LOCAL APP SETUP DEFERRED: {exc}", file=sys.stderr)
        return 1

    print("Local application setup complete. Start it with `npm start`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
