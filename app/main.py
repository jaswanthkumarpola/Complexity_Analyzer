"""
FastAPI application entry point.
Serves both the REST API and the static frontend from a single origin.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.utils.errors import AnalysisError, analysis_error_handler, generic_error_handler

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
settings = get_settings()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info(
        "AI provider configured: %s (provider: %s, model: %s)",
        settings.ai_provider_configured,
        settings.ai_provider,
        settings.ai_model,
    )
    if not settings.ai_provider_configured:
        logger.warning(
            "No valid AI_API_KEY configured. Analysis will use static rules and fallback mode. "
            "Set AI_API_KEY in your .env file to enable AI-assisted analysis."
        )
    yield  # Application runs here


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-assisted complexity analysis tool for source code. "
        "Combines static structural analysis with an optional LLM for explanations."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

# ---------------------------------------------------------------------------
# Custom exception handlers
# ---------------------------------------------------------------------------
app.add_exception_handler(AnalysisError, analysis_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
app.include_router(router)

# ---------------------------------------------------------------------------
# Static files (frontend)
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).parent / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the main frontend HTML page."""
    index = STATIC_DIR / "index.html"
    return FileResponse(str(index))


