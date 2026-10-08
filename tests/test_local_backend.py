from __future__ import annotations

import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from running_coach_app.api import HEALTH_RESPONSE, create_app
from running_coach_app.server import DEFAULT_PORT, HOST


async def asgi_get(app, path: str) -> tuple[int, dict[str, str], bytes]:
    messages: list[dict] = []
    request_sent = False

    async def receive() -> dict:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 50000),
            "server": (HOST, DEFAULT_PORT),
            "root_path": "",
        },
        receive,
        send,
    )

    start = next(message for message in messages if message["type"] == "http.response.start")
    headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start.get("headers", [])
    }
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], headers, body


class LocalBackendTest(unittest.TestCase):
    def test_health_response_is_exact_and_private_state_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            private_marker = Path(directory) / "private-athlete-value"
            private_marker.write_text("must-not-be-returned", encoding="utf-8")
            app = create_app(Path(directory) / "missing-frontend")

            status, headers, body = asyncio.run(asgi_get(app, "/api/health"))

        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(json.loads(body), HEALTH_RESPONSE)
        self.assertNotIn(b"must-not-be-returned", body)

    def test_server_defaults_are_loopback_only(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")
        self.assertEqual(DEFAULT_PORT, 8000)

    def test_compiled_frontend_is_served_at_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            (frontend / "index.html").write_text(
                "<!doctype html><h1>Running Coach is ready</h1>",
                encoding="utf-8",
            )
            app = create_app(frontend)

            status, headers, body = asyncio.run(asgi_get(app, "/"))

        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertIn(b"Running Coach is ready", body)

    def test_backend_source_has_no_private_data_integration(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "src" / "running_coach_app" / "api.py").read_text(
            encoding="utf-8"
        ).lower()
        for forbidden in ("running_data.db", "garmindb", "sqlite3", "credentials", "route_coordinates"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
