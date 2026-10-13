"""
FastAPI route definitions for all API endpoints.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    ConfigStatusResponse,
    DetectLanguageRequest,
    DetectLanguageResponse,
    HealthResponse,
    LanguageCapability,
    LanguagesResponse,
)
from app.config import get_settings
from app.core.analysis_pipeline import run_analysis
from app.core.language_detection import detect_language
from app.core.language_registry import all_languages
from app.core.language_validation import validate_language_selection
from app.utils.errors import ProviderError
from app.utils.validation import (
    decode_file_content,
    sanitize_filename,
    validate_code_not_empty,
    validate_code_size,
    validate_file_extension,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _provider_http_error(exc: ProviderError) -> HTTPException:
    """Turn an AI failure into a readable HTTP error (frontend shows `detail`)."""
    logger.error("AI provider error: %s", exc)
    return HTTPException(status_code=exc.status_code, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    """Return application health and configuration summary."""
    settings = get_settings()
    modes = ["static_analysis"]
    if settings.ai_provider_configured:
        modes.append("ai_assisted")
    modes.append("fallback")
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        app_name=settings.app_name,
        ai_provider_configured=settings.ai_provider_configured,
        analysis_modes=modes,
    )


# ---------------------------------------------------------------------------
# GET /api/languages
# ---------------------------------------------------------------------------

@router.get("/languages", response_model=LanguagesResponse, tags=["Languages"])
async def list_languages() -> LanguagesResponse:
    """Return all registered languages and their analysis capabilities."""
    caps = [
        LanguageCapability(
            identifier=lang.identifier,
            display_name=lang.display_name,
            extensions=lang.extensions,
            parser_available=lang.parser_available,
            static_analysis=lang.static_analysis,
            known_limitations=lang.known_limitations,
        )
        for lang in all_languages()
    ]
    return LanguagesResponse(languages=caps, total=len(caps))


# ---------------------------------------------------------------------------
# POST /api/detect-language
# ---------------------------------------------------------------------------

@router.post("/detect-language", response_model=DetectLanguageResponse, tags=["Languages"])
async def detect_language_endpoint(req: DetectLanguageRequest) -> DetectLanguageResponse:
    """Detect the programming language of submitted source code."""
    validate_code_not_empty(req.code)
    validate_code_size(req.code)
    lang, method, confidence = detect_language(req.code, filename=req.filename)
    return DetectLanguageResponse(
        language=lang.identifier,
        display_name=lang.display_name,
        confidence=confidence,
        detection_method=method,
    )


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze(req: AnalyzeRequest) -> AnalysisResponse:
    """
    Analyze source code and return time/space complexity predictions.
    Accepts JSON body with code, optional language override, and settings.
    """
    validate_code_size(req.code)
    # Enforce a manual language selection BEFORE any analysis or AI call.
    validate_language_selection(req.code, req.language)
    try:
        return await run_analysis(
            code=req.code,
            language_override=req.language,
            filename=req.filename,
            settings=req.settings,
        )
    except HTTPException:
        raise
    except ProviderError as exc:
        raise _provider_http_error(exc) from exc
    except Exception as exc:
        logger.error("Analysis error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {type(exc).__name__}: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# POST /api/analyze-file
# ---------------------------------------------------------------------------

@router.post("/analyze-file", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
) -> AnalysisResponse:
    """
    Accept a source-code file upload and return complexity analysis.
    The file is decoded and analyzed identically to POST /api/analyze.
    The file content is never executed.
    """
    safe_name = sanitize_filename(file.filename)
    if not safe_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required.",
        )

    validate_file_extension(safe_name)

    raw = await file.read()
    settings = get_settings()
    if len(raw) > settings.max_code_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_code_size_kb} KB.",
        )

    code = decode_file_content(raw, safe_name)
    validate_code_not_empty(code)
    # Enforce a manual language selection BEFORE any analysis or AI call.
    validate_language_selection(code, language)

    try:
        return await run_analysis(
            code=code,
            language_override=language,
            filename=safe_name,
        )
    except HTTPException:
        raise
    except ProviderError as exc:
        raise _provider_http_error(exc) from exc
    except Exception as exc:
        logger.error("File analysis error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File analysis failed: {type(exc).__name__}: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# GET /api/config/status
# ---------------------------------------------------------------------------

@router.get("/config/status", response_model=ConfigStatusResponse, tags=["System"])
async def config_status() -> ConfigStatusResponse:
    """Return safe configuration status. Never returns secrets."""
    settings = get_settings()
    modes = ["static_analysis", "fallback"]
    if settings.ai_provider_configured:
        modes.append("ai_assisted")
    return ConfigStatusResponse(
        ai_provider_configured=settings.ai_provider_configured,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model if settings.ai_provider_configured else "N/A",
        analysis_modes_available=modes,
        max_code_size_kb=settings.max_code_size_kb,
    )