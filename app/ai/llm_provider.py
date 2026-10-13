"""
OpenAI-compatible LLM provider.
Supports any API that is compatible with the OpenAI Chat Completions endpoint,
including OpenAI, Together AI, Groq, Mistral, and self-hosted models.

Every failure (missing key, timeout, network, auth, rejected request,
empty/truncated/malformed output) raises ProviderError with a readable message.
This provider never returns a guessed or default complexity.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.ai.base_provider import AIAnalysisResult, BaseAIProvider
from app.ai.prompts import SYSTEM_PROMPT, build_analysis_prompt
from app.config import get_settings
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_MAX_OUTPUT_TOKENS = 4096  # schema asks for up to 800-word explanation + optimizations


class LLMProvider(BaseAIProvider):
    """OpenAI-compatible provider. Sends structured prompts and validates JSON responses."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.ai_provider_configured:
            raise ProviderError(
                "AI provider is not configured: AI_API_KEY is missing or still a placeholder.",
                status_code=503,
            )
        self._api_key = settings.ai_api_key.strip()
        self._model = settings.ai_model.strip()
        self._base_url = settings.ai_base_url.strip().rstrip("/")
        self._timeout = settings.ai_timeout_seconds
        self._max_attempts = max(1, settings.ai_max_retries)

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def is_fallback(self) -> bool:
        return False

    async def analyze(
        self,
        code: str,
        language: str,
        static_summary: str,
    ) -> AIAnalysisResult:
        """Call the Chat Completions API and return a validated result, or raise ProviderError."""
        user_prompt = build_analysis_prompt(code, language, static_summary)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        # Parameters some models/providers reject; dropped/renamed on a 400 that names them.
        token_param = "max_tokens"
        send_temperature = True
        send_response_format = True
        adaptations = 0

        last_error: Optional[ProviderError] = None
        attempt = 0

        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            while attempt < self._max_attempts:
                payload: Dict[str, Any] = {"model": self._model, "messages": messages}
                payload[token_param] = _MAX_OUTPUT_TOKENS
                if send_temperature:
                    payload["temperature"] = 0.1
                if send_response_format:
                    payload["response_format"] = {"type": "json_object"}

                try:
                    resp = await client.post(url, json=payload, headers=headers)
                except httpx.TimeoutException:
                    last_error = ProviderError(
                        f"AI request timed out after {self._timeout}s "
                        f"(model '{self._model}'). Increase AI_TIMEOUT_SECONDS or try again.",
                        status_code=504,
                    )
                    logger.warning("AI timeout (attempt %d/%d)", attempt + 1, self._max_attempts)
                except httpx.RequestError as exc:
                    last_error = ProviderError(
                        f"Could not reach the AI endpoint {self._base_url}: "
                        f"{type(exc).__name__}: {exc}. Check AI_BASE_URL and your network.",
                        status_code=502,
                    )
                    logger.warning("AI network error (attempt %d/%d): %s", attempt + 1, self._max_attempts, exc)
                else:
                    code_ = resp.status_code
                    if code_ == 200:
                        try:
                            return self._parse_response(resp)
                        except ProviderError as exc:
                            last_error = exc
                            logger.warning(
                                "AI response unusable (attempt %d/%d): %s",
                                attempt + 1, self._max_attempts, exc,
                            )
                    elif code_ in (401, 403):
                        raise ProviderError(
                            f"AI provider rejected the API key (HTTP {code_}): "
                            f"{_error_message(resp)}. Check AI_API_KEY.",
                            status_code=502,
                        )
                    elif code_ in (400, 404, 422):
                        detail = _error_message(resp)
                        low = detail.lower()
                        changed = False
                        if token_param == "max_tokens" and "max_completion_tokens" in low:
                            token_param, changed = "max_completion_tokens", True
                        if send_temperature and "temperature" in low:
                            send_temperature, changed = False, True
                        if send_response_format and ("response_format" in low or "json_object" in low):
                            send_response_format, changed = False, True
                        if changed and adaptations < 3:
                            adaptations += 1
                            logger.info("Adjusting AI request parameters and retrying: %s", detail)
                            continue  # does not consume an attempt
                        raise ProviderError(
                            f"AI provider rejected the request (HTTP {code_}): {detail}",
                            status_code=502,
                        )
                    elif code_ in _RETRYABLE_STATUS:
                        last_error = ProviderError(
                            f"AI provider returned HTTP {code_}: {_error_message(resp)}",
                            status_code=503 if code_ == 429 else 502,
                        )
                        logger.warning("AI HTTP %d (attempt %d/%d)", code_, attempt + 1, self._max_attempts)
                    else:
                        raise ProviderError(
                            f"AI provider returned unexpected HTTP {code_}: {_error_message(resp)}",
                            status_code=502,
                        )

                attempt += 1
                if attempt < self._max_attempts:
                    await asyncio.sleep(min(2 ** (attempt - 1), 4))

        assert last_error is not None
        raise ProviderError(
            f"AI analysis failed after {self._max_attempts} attempt(s): {last_error}",
            status_code=last_error.status_code,
        ) from last_error

    def _parse_response(self, resp: httpx.Response) -> AIAnalysisResult:
        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderError("AI provider returned a non-JSON HTTP body.", 502) from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        if not choices or not isinstance(choices, list) or not isinstance(choices[0], dict):
            raise ProviderError(
                f"AI provider response contained no choices: {str(data)[:300]}", 502
            )
        choice = choices[0]
        finish = choice.get("finish_reason")
        content = (choice.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderError(
                f"AI provider returned an empty message (finish_reason={finish}).", 502
            )

        try:
            parsed = _parse_json_response(content)
        except (json.JSONDecodeError, ValueError) as exc:
            if finish == "length":
                raise ProviderError(
                    "AI response was cut off at the token limit before the JSON completed.", 502
                ) from exc
            raise ProviderError(
                f"AI returned malformed JSON ({exc}). Start of reply: {content[:200]!r}", 502
            ) from exc

        model = data.get("model") if isinstance(data.get("model"), str) else self._model
        try:
            return _build_result(parsed, model or self._model)
        except (ValueError, TypeError) as exc:
            raise ProviderError(f"AI returned an invalid analysis: {exc}", 502) from exc


def _error_message(resp: httpx.Response) -> str:
    """Best-effort extraction of a provider error message."""
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:400]
        if isinstance(err, str):
            return err[:400]
        if isinstance(body, dict) and body.get("message"):
            return str(body["message"])[:400]
    except ValueError:
        pass
    return (resp.text or "no response body")[:400]


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Extract and parse a JSON object from the model's text response."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end <= start:
            raise
        parsed = json.loads(content[start:end])

    if not isinstance(parsed, dict):
        raise ValueError("top-level JSON value is not an object")
    return parsed


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None and str(v).strip()]
    return [str(value)]


def _build_result(data: Dict[str, Any], model: str) -> AIAnalysisResult:
    """Convert parsed JSON dict to AIAnalysisResult, with strict validation."""
    required = ("time_complexity", "space_complexity", "explanation")
    missing = [k for k in required if not _opt_str(data.get(k))]
    if missing:
        raise ValueError(f"missing or empty required fields: {missing}")

    time_c = str(data["time_complexity"]).strip()
    space_c = str(data["space_complexity"]).strip()
    for label, val in (("time_complexity", time_c), ("space_complexity", space_c)):
        if "(" not in val:
            raise ValueError(f"{label} {val!r} is not a Big-O style expression")

    raw_opts = data.get("optimizations")
    validated_opts: List[Dict[str, Any]] = []
    if isinstance(raw_opts, list):
        for opt in raw_opts[:5]:
            if isinstance(opt, dict) and "title" in opt and "proposed_change" in opt:
                validated_opts.append(opt)

    confidence = data.get("confidence", "Low")
    if confidence not in ("High", "Medium", "Low", "Unknown"):
        confidence = "Low"

    return AIAnalysisResult(
        time_complexity=time_c,
        space_complexity=space_c,
        explanation=str(data["explanation"])[:4000],
        best_case=_opt_str(data.get("best_case")),
        average_case=_opt_str(data.get("average_case")),
        worst_case=_opt_str(data.get("worst_case")),
        assumptions=_str_list(data.get("assumptions")),
        optimizations=validated_opts,
        confidence=confidence,
        warnings=_str_list(data.get("warnings")),
        provider="openai_compatible",
        model=model,
        is_fallback=False,
        raw=data,
    )