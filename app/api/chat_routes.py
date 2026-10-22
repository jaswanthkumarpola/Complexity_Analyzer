"""
POST /api/chat — conversational assistant about the user's code and analysis.
"""
from __future__ import annotations

import logging
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.ai.chat_service import build_system_prompt, check_rate_limit, generate_reply
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

MAX_HISTORY_MESSAGES = 12


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatAnalysisContext(BaseModel):
    """Compact summary of the latest analysis shown in the UI."""
    language: Optional[str] = Field(None, max_length=60)
    method: Optional[str] = Field(None, max_length=40)
    time_complexity: Optional[str] = Field(None, max_length=80)
    time_confidence: Optional[str] = Field(None, max_length=20)
    space_complexity: Optional[str] = Field(None, max_length=80)
    space_confidence: Optional[str] = Field(None, max_length=20)
    best_case: Optional[str] = Field(None, max_length=80)
    average_case: Optional[str] = Field(None, max_length=80)
    worst_case: Optional[str] = Field(None, max_length=80)
    explanation: Optional[str] = Field(None, max_length=4000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=40)
    code: Optional[str] = Field(None, max_length=500_000)
    analysis: Optional[ChatAnalysisContext] = None


class ChatResponse(BaseModel):
    reply: str
    model: str


def _client_id(request: Request) -> str:
    # Behind a proxy (Render, Railway, ...) the real client is in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Answer a question about complexity, the user's code, or the latest analysis."""
    if req.messages[-1].role != "user":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The last message must come from the user.",
        )

    retry_after = check_rate_limit(_client_id(request))
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many messages. Please wait {retry_after}s and try again.",
            headers={"Retry-After": str(retry_after)},
        )

    system_prompt = build_system_prompt(
        req.code, req.analysis.model_dump(exclude_none=True) if req.analysis else None
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in req.messages[-MAX_HISTORY_MESSAGES:]
    ]

    try:
        reply, model = await generate_reply(system_prompt, history)
    except ProviderError as exc:
        logger.error("Chat provider error: %s", exc)
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Unexpected chat error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {type(exc).__name__}",
        ) from exc

    return ChatResponse(reply=reply, model=model)