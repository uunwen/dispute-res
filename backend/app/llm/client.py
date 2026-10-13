import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar, Union, get_args, get_origin

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.profiling import current_stage, profiler

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def model_for_role(role: str) -> str:
    """Resolve the effective model for an agent role, defaulting to LLM_MODEL."""
    mapping = {
        "advocate": settings.llm_model_advocate,
        "judge": settings.llm_model_judge,
        "tools": settings.llm_model_tools,
    }
    return mapping.get(role) or settings.llm_model


class LLMError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    extra_content: dict = field(default_factory=dict)


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResult:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage | None = None


def _mock_value(annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Union:
        for arg in args:
            if arg is not type(None):
                return _mock_value(arg)
        return None
    if origin in (list, set, tuple, frozenset):
        return []
    if origin is dict:
        return {}
    if origin is not None:
        return _mock_value(args[0]) if args else None

    if annotation is str:
        return "mock"
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    if annotation is type(None):
        return None

    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return _mock_instance(annotation)
        if issubclass(annotation, Enum):
            return next(iter(annotation))
    return None


def _mock_instance(schema: type[T]) -> T:
    try:
        return schema()
    except Exception:
        pass

    kwargs = {}
    for name, f in schema.model_fields.items():
        if f.is_required():
            kwargs[name] = _mock_value(f.annotation)
    return schema(**kwargs)


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, mock=None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.mock = settings.llm_mock if mock is None else mock
        self.timeout = settings.llm_timeout
        self.max_retries = settings.llm_max_retries
        self.backoff_base = settings.llm_backoff_base
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
        self.degraded = False
        self.error_info: dict | None = None

    @property
    def configured(self) -> bool:
        return self.mock or bool(self.api_key)

    def _mark_degraded(self, error_class: str, status: int | None = None) -> None:
        self.degraded = True
        if self.error_info is None:
            self.error_info = {"class": error_class, "status": status}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _base_payload(self, messages: list[dict], model: str | None = None) -> dict:
        payload: dict = {
            "model": model or self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        return payload

    async def structured(
        self, system: str, user: str, schema: type[T], *, role: str = "advocate", retries: int = 1
    ) -> T | None:
        if self.mock:
            return _mock_instance(schema)
        if not self.api_key:
            self._mark_degraded("ConfigurationError")
            return None

        messages = [
            {"role": "system", "content": self._with_schema(system, schema)},
            {"role": "user", "content": user},
        ]
        for attempt in range(retries + 1):
            content = await self._complete_content(messages, json_mode=True, role=role)
            try:
                return schema.model_validate_json(content)
            except (ValidationError, json.JSONDecodeError) as exc:
                if attempt >= retries:
                    raise LLMError(
                        f"structured output failed validation after {retries} retry(s): {exc}"
                    ) from exc
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Your previous response was invalid JSON: {exc}. "
                        "Respond again with only a JSON object matching the schema.",
                    }
                )
        raise LLMError("unreachable")

    async def chat(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        tool_choice: str | dict = "auto",
        temperature: float | None = None,
        role: str = "tools",
    ) -> ChatResult:
        if self.mock:
            return ChatResult(content="This is a mock response.", tool_calls=[], usage=Usage())

        if not self.api_key:
            self._mark_degraded("ConfigurationError")
            raise LLMError("no API key configured and mock mode is disabled")

        payload = self._base_payload(messages, model_for_role(role))
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        start = time.perf_counter()
        data = await self._request(payload)
        self._log_usage(data.get("usage"))
        self._record(current_stage.get() or f"llm_{role}", time.perf_counter() - start, data.get("usage"))
        return self._parse_chat_result(data)

    async def _complete_content(
        self, messages: list[dict], *, json_mode: bool = False, role: str = "advocate"
    ) -> str:
        payload = self._base_payload(messages, model_for_role(role))
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        start = time.perf_counter()
        data = await self._request(payload)
        self._log_usage(data.get("usage"))
        self._record(current_stage.get() or f"llm_{role}", time.perf_counter() - start, data.get("usage"))
        return data["choices"][0]["message"]["content"]

    async def _request(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            for attempt in range(self.max_retries + 1):
                try:
                    resp = await http.post(url, headers=self._headers(), json=payload)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in _RETRYABLE_STATUS or attempt >= self.max_retries:
                        self._mark_degraded("HTTPStatusError", exc.response.status_code)
                        if exc.response.status_code == 404:
                            raise LLMError(
                                "LLM HTTP 404 — model or endpoint not found; check LLM_MODEL / LLM_BASE_URL"
                            ) from exc
                        raise LLMError(f"LLM HTTP error {exc.response.status_code}") from exc
                    logger.warning(
                        "LLM HTTP %s; retrying (attempt %d)", exc.response.status_code, attempt + 1
                    )
                    await self._backoff(attempt)
                except httpx.TimeoutException as exc:
                    if attempt >= self.max_retries:
                        self._mark_degraded("TimeoutException")
                        raise LLMError(f"LLM timeout after retries: {exc}") from exc
                    await self._backoff(attempt)
                except httpx.TransportError as exc:
                    if attempt >= self.max_retries:
                        self._mark_degraded("TransportError")
                        raise LLMError(f"LLM transport error after retries: {exc}") from exc
                    await self._backoff(attempt)
        raise LLMError("unreachable")

    async def _backoff(self, attempt: int) -> None:
        wait = self.backoff_base * (2 ** attempt)
        logger.warning("LLM transient error; retrying in %.2fs (attempt %d)", wait, attempt + 1)
        await asyncio.sleep(wait)

    def _parse_chat_result(self, data: dict) -> ChatResult:
        message = data["choices"][0]["message"]
        tool_calls = [
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                arguments=json.loads(tc["function"]["arguments"]),
                extra_content={
                    k: v for k, v in tc.items() if k not in ("id", "type", "function")
                },
            )
            for tc in (message.get("tool_calls") or [])
        ]
        usage = data.get("usage")
        return ChatResult(
            content=message.get("content"),
            tool_calls=tool_calls,
            usage=Usage(**usage) if usage else None,
        )

    def _log_usage(self, usage: dict | None) -> None:
        if usage:
            logger.info(
                "LLM token usage: prompt=%s completion=%s total=%s",
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )

    def _record(self, stage: str, seconds: float, usage: dict | None) -> None:
        u = usage or {}
        profiler.record(
            stage,
            seconds,
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
        )

    @staticmethod
    def _with_schema(system: str, schema: type[BaseModel]) -> str:
        return f"{system}\n\nRespond with a single JSON object matching this JSON Schema:\n{schema.model_json_schema()}"


def log_llm_config() -> None:
    """Log the effective LLM/embedding configuration (without the API key)."""
    chat_url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    embed_base = settings.embedding_base_url or settings.llm_base_url
    embed_url = f"{embed_base.rstrip('/')}/embeddings"
    logger.info(
        "LLM config: base_url=%s chat_url=%s model=%s mock=%s",
        settings.llm_base_url,
        chat_url,
        settings.llm_model,
        settings.llm_mock,
    )
    logger.info(
        "LLM models: advocate=%s judge=%s tools=%s",
        model_for_role("advocate"),
        model_for_role("judge"),
        model_for_role("tools"),
    )
    logger.info("Embeddings config: model=%s url=%s", settings.embedding_model, embed_url)


client = LLMClient()
