"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import auth_routes, feedback_routes, legal_routes, watch_routes
from .config import get_settings
from .db import init_db
from .volvo import api_status


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="VolvoWatch backend", version="0.0.1", lifespan=lifespan)

# The watch is not a browser and the /link pages are same-origin, so no CORS is
# needed. Only added if EXTRA_ALLOWED_ORIGINS is explicitly configured.
_settings = get_settings()
if _settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(auth_routes.router)
app.include_router(legal_routes.router)
app.include_router(feedback_routes.router)
app.include_router(watch_routes.router)

# Shared design-system CSS + self-hosted fonts for the server-rendered pages
# (/link, /auth/callback, /terms, /privacy) — same source as the static
# marketing site, so the browser-facing pages don't drift from it.
app.mount(
    "/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static"
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.get("/volvo-status")
async def volvo_status() -> dict:
    try:
        return await api_status()
    except Exception:  # noqa: BLE001 — unauthenticated endpoint, don't leak detail
        return {"ok": False, "error": "could not reach the Volvo status service"}


# The static marketing landing page owns "/" — mounted last, after every other
# route, since Starlette dispatches to the first matching route in
# registration order and a root-prefix Mount matches any path. StaticFiles
# only ever sees requests nothing above already claimed.
app.mount(
    "/",
    StaticFiles(directory=Path(__file__).parent / "landing", html=True),
    name="landing",
)
