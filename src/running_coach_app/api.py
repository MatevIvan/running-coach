"""FastAPI application with a public health check and compiled frontend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles


HEALTH_RESPONSE: Final[dict[str, str]] = {
    "status": "ok",
    "service": "running-coach",
    "api_version": "1",
}


def default_frontend_directory() -> Path:
    configured_root = os.environ.get("RUNNING_COACH_PROJECT_ROOT")
    project_root = (
        Path(configured_root).expanduser().resolve()
        if configured_root
        else Path(__file__).resolve().parents[2]
    )
    return project_root / "frontend" / "dist"


def create_app(frontend_directory: Path | None = None) -> FastAPI:
    app = FastAPI(title="Running Coach", version="1", docs_url=None, redoc_url=None)

    @app.get("/api/health", response_class=JSONResponse)
    async def health() -> dict[str, str]:
        return dict(HEALTH_RESPONSE)

    static_directory = frontend_directory or default_frontend_directory()
    if static_directory.is_dir():
        app.mount("/", StaticFiles(directory=static_directory, html=True), name="frontend")

    return app


app = create_app()
