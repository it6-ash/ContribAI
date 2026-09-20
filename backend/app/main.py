import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import get_settings
from . import db as db_module
from .db import init_db
from .github import RateLimited
from .scheduler import refresher
from .seed import seed_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
)
log = logging.getLogger("contribai")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.check()
    init_db()
    if settings.is_production:
        # Seeding here would write 5 fabricated repositories and 23 fabricated
        # issues into a real database, where users would see them as real.
        log.info("production mode: demo corpus not seeded, demo sign-in disabled")
    else:
        # Module attribute, not a bound import, so tests can swap the session factory.
        with db_module.SessionLocal() as db:
            result = seed_all(db)
        log.info("demo corpus ready: %s", result)
    refresher.start()
    try:
        yield
    finally:
        await refresher.stop()


app = FastAPI(
    title="ContribAI",
    description="AI open-source contribution navigator. Matches developers to issues they can actually ship.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimited)
async def rate_limited_handler(request: Request, exc: RateLimited) -> JSONResponse:
    """Surface GitHub's limit as a countdown the UI can render, never a silent failure."""
    minutes = exc.seconds_remaining // 60 + 1
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"GitHub data refresh available in {minutes} minute{'s' if minutes != 1 else ''}",
            "retry_after_seconds": exc.seconds_remaining,
        },
        headers={"Retry-After": str(exc.seconds_remaining)},
    )


app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"service": "contribai", "docs": "/docs", "api": "/api/health"}
