"""FastAPI application entrypoint (design §6.2)."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import episodes, jobs, personas, projects, source_summary, sources
from .db import close_pool

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Podcast Synthesis API",
    version=__version__,
    summary="Material -> persona-grounded podcast (MVP, Milestone 1 skeleton).",
)

# CORS for the future Next.js frontend (design §7). Tighten origins per env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(sources.router)
app.include_router(source_summary.router)
app.include_router(personas.router)
app.include_router(episodes.router)
app.include_router(jobs.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}


@app.on_event("shutdown")
def _shutdown() -> None:
    close_pool()
