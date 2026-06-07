"""FastAPI application entrypoint (design §6.2)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api import (audio, episodes, export, jobs, meta, personas, projects, qa,
                  scripts, source_summary, sources)
from .db import close_pool

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    close_pool()


app = FastAPI(
    title="Podcast Synthesis API",
    version=__version__,
    summary="Material -> persona-grounded podcast (MVP backend).",
    lifespan=lifespan,
)

# CORS for the future Next.js frontend (design §7). Tighten origins per env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Consistent, human-readable error envelope (design §18).
@app.exception_handler(HTTPException)
async def _http_exc(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"type": "http_error", "message": exc.detail}},
                        headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def _validation_exc(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422,
                        content={"error": {"type": "validation_error",
                                           "message": "The request was invalid.",
                                           "details": exc.errors()}})


@app.exception_handler(Exception)
async def _unhandled_exc(_request: Request, exc: Exception):
    logging.exception("unhandled error")
    return JSONResponse(status_code=500,
                        content={"error": {"type": "server_error",
                                           "message": "Something went wrong. Please retry."}})


for _r in (projects, sources, source_summary, personas, episodes, scripts, qa,
           audio, export, meta, jobs):
    app.include_router(_r.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}
