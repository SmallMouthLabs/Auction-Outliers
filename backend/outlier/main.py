"""FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api import routes_analysis, routes_comps, routes_listings, routes_misc
from .config import get_settings
from .db import init_db
from .jobs import handlers  # noqa: F401  (register handlers)
from .jobs.queue import Worker
from .providers.base import BudgetExceeded, ProviderError, ProviderNotConfigured

log = logging.getLogger("outlier")


def create_app(run_worker: bool | None = None) -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=getattr(logging, s.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    worker = Worker(poll_seconds=s.worker_poll_seconds)
    use_worker = s.run_worker if run_worker is None else run_worker

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        if use_worker:
            worker.start()
            log.info("background worker started")
        log.info("OUTLIER backend %s ready (data dir: %s)", __version__, s.data_dir)
        yield
        if use_worker:
            worker.stop()

    app = FastAPI(title="OUTLIER API", version=__version__, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(routes_listings.router)
    app.include_router(routes_listings.image_router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_comps.router)
    app.include_router(routes_comps.providers_router)
    app.include_router(routes_misc.router)

    @app.exception_handler(ProviderNotConfigured)
    async def _not_configured(_: Request, exc: ProviderNotConfigured):
        return JSONResponse(status_code=424, content={"detail": str(exc), "code": "provider_not_configured"})

    @app.exception_handler(BudgetExceeded)
    async def _budget(_: Request, exc: BudgetExceeded):
        return JSONResponse(status_code=429, content={"detail": str(exc), "code": "budget_exceeded"})

    @app.exception_handler(ProviderError)
    async def _provider(_: Request, exc: ProviderError):
        return JSONResponse(status_code=502, content={"detail": str(exc), "code": "provider_error"})

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app


app = create_app()
