"""Command-line entry point for the loopback-only local server."""

from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser

import uvicorn

from .api import default_frontend_directory


HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the local Running Coach application.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args


def open_browser_when_ready(port: int) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.25):
                webbrowser.open(f"http://{HOST}:{port}")
                return
        except OSError:
            time.sleep(0.1)


def main() -> int:
    args = parse_args()
    frontend = default_frontend_directory()
    if not args.reload and not (frontend / "index.html").is_file():
        raise SystemExit(
            f"Compiled frontend not found at {frontend}. Run `npm run build` first."
        )

    if args.open_browser:
        threading.Thread(
            target=open_browser_when_ready,
            args=(args.port,),
            daemon=True,
        ).start()

    uvicorn.run(
        "running_coach_app.api:app",
        host=HOST,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
